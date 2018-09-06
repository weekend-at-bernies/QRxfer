import WorkerManager
import FilePathWrapper
import Settings
import PIL
from PIL import Image
import cv2
import cv
import zbar
import os
import sys
import shutil
import PngUtils
import FileUtils
from Dimension import Dimension
from Dimension import getInverted
from WorkerManager import WorkerType
from WorkerManager import WorkerStatus
import XmlUtils
import Utils

# Requires package '$ sudo apt-get install python-tk python-pil.imagetk':
#import Tkinter
#import ImageTk



class FatalDecodeError(Exception):
    def __init__(self, s):
        self.s = s
    def __str__(self):
        return repr(self.s)

# This describes QRCodes in the following forms:
# Matrix of QRCodes
# Row of QRcode(s)
# Column of QRCode(s)
class QRCode(WorkerManager.Worker, WorkerManager.WorkerManager):


    # IN: 
    # png: png package wrapper around target QR code(s)
    # output_fw: <path to>/decode/attemptY/setX/ [matrixA/rowB/qrC/]                 <--- where the processed png will be output
    # dimension: dimension of the pngpackage (matrix, row/col or single QR code)
    # xmlmergemanager 
    # xml : <matrix> <row> <col> or <QR> node
    def __init__(self, manager, png, output_fw, dimension, xmlmerged, xml):
        # Invoke the super (WorkerManager.Worker) class constructor:
        super(QRCode, self).__init__(manager)
        self.png = png
        self.output_fw = output_fw
        self.dimension = dimension 
        self.xmlmerged = xmlmerged
        self.xml = xml
        

    # Example:
    # self.dimension == Dimension.matrix
    # self.xml: <matrix='0'></matrix>
    # self.output_fw == /tmp/sprog/bopeep/decode/attempt0/set0     (dir exists, this is where 'matrix0.png' should be copied)
    # nextoutput_fw: /tmp/sprog/bopeep/decode/attempt0/set0/matrix-0          
    # nextdimension: row 
    def work(self, rtargs=None):
        self.prework()

        status = WorkerStatus.completed_success

       # print "Analyzing: %s (%s)"%(Utils.prettyPrint1(self.xml), Utils.prettyPrint2(self.xml))

        # Get nextdimension
        nextdimension = self.dimension.next()

        strtarget = "%s-%s"%(str(self.dimension), self.xml.get(Settings.index_attrib))
        nextoutput_fw = self.output_fw.getExtended("%s"%(strtarget))
           
        if not nextoutput_fw.createDir():
            raise OSError("Could not create directory: %s"%(nextoutput_fw.getPath()))  


        # FIXME: Writing the image processing artefacts to disk is not strictly necessary:
        if Settings.dump_artefacts:
            if self.dimension == Dimension.matrix:
                shutil.copy(str(self.png.img_fw), str(self.output_fw))
            else:
                pngfile = "%s/%s.png"%(self.output_fw.getPath(), strtarget)
                cv2.imwrite(pngfile, self.png.getImgCV2())

        ###################################################################################################

        # PROCESSING A MATRIX OF QR CODES:
        if nextdimension != None:              
            coordspace = self.getCoordSpace(self.png, Settings.region_tolerance, nextdimension)
            self.verifyCoordSpace(nextdimension, coordspace)

            i = 0
            for coords in coordspace:


                nextpng = self.getRegion(self.png, nextdimension, coords)


                # PHASE IN:
                if self.xmlmerged is not None:
                    nextxmlmerged = self.xmlmerged.find("%s[@%s='%d']"%(str(nextdimension), Settings.index_attrib, i))
                    if nextxmlmerged is not None:
                        if Utils.isDecoded(nextxmlmerged):
                            # DECODED ALREADY
                           # print "Already processed (skipping): %s"%(Utils.prettyPrint1(nextxmlmerged)) 
                            i += 1
                            continue 
                else:
                    nextxmlmerged = None
                nextxml = XmlUtils.getOrAddChild(self.xml, str(nextdimension), {Settings.index_attrib:str(i)})


                qrcode = QRCode(self, nextpng, nextoutput_fw, nextdimension, nextxmlmerged, nextxml)

                # Schedule a worker:
                self.scheduleWorker(qrcode, qrcode.work) 

                i += 1 

            # Start the workers:
            self.startWorkers()

            # All workers complete without error?
            if not self.joinWorkers():
                raise FatalDecodeError(str(self))

                    
        ###################################################################################################

        # PROCESSING A SINGLE QR CODE
        else:
            data1 = self.decode(self.png, Settings.maxpayloadsize, Settings.minimum_resize_dimension, Settings.resize_increment, True) 
            if len(data1) < Settings.maxpayloadsize:
                # Suboptimal? Try instead applying a up-resize strategy:
                data2 = self.decode(self.png, Settings.maxpayloadsize, Settings.maximum_resize_dimension, Settings.resize_increment, False) 
                if (len(data1) > len(data2)):
                    data = data1
                else:
                    data = data2
            else:
                data = data1
            if len(data) >= Settings.minpayloadsize:
                #print "DECODE SUCCESS: %s (%s)"%(Utils.prettyPrint1(self.xml), Utils.prettyPrint2(self.xml))
                try:
                    FileUtils.writeToFile((nextoutput_fw.getExtended("/%s.txt"%(strtarget))).getPath(), data)
                    self.xml.text = "1"
                    # First time round, self.xmlmerged will be None
                    if self.xmlmerged is not None:
                        
                        if self.xmlmerged.text == "0":
                            #print "UPDATING: %s"%(Utils.prettyPrint1(self.xmlmerged))
                            self.xmlmerged.text = "1"

                except IOError:
                #    print "Could not write: %s"%(data_fw.getPath())
                    status = WorkerStatus.completed_fatal_error
                # FIXME : return me out of here!
            else:
                #print "DECODE FAILURE: %s (%s)"%(Utils.prettyPrint1(self.xml), Utils.prettyPrint2(self.xml))
                self.xml.text = "0"
                status = WorkerStatus.completed_not_successful

        ###################################################################################################
            
        # Finish work:   
        self.postwork(status)

    ###################################################################################################

    def getCoordSpace(self, png, tolerance, dimension):  
        img_rgb = png.getImgPIL().convert('RGB')    
        if dimension == Dimension.qr:
            dimension = getInverted(Settings.first_dimension)#dimension.getFirstInverted()    
        if dimension == Dimension.row: 
            coordspace = PngUtils.filterRegions(PngUtils.getRows(img_rgb), tolerance)   
        elif dimension == Dimension.col:
            coordspace = PngUtils.filterRegions(PngUtils.getCols(img_rgb), tolerance)
        else:
            raise ValueError("Invalid dimension specified: %s"%(dimension))
        return coordspace

    def verifyCoordSpace(self, dimension, coordspace):
        numdimensions = -1
        if dimension == Dimension.qr:
            dimension = getInverted(Settings.first_dimension)#dimension.getFirstInverted()
        if dimension == Dimension.row:
            numdimensions = Settings.expected_num_rows
        elif dimension == Dimension.col:
            numdimensions = Settings.expected_num_cols
        #if (self.index < (self.manager.getWorkerCount() - 1)) and (numdimensions >= 0) and (numdimensions != len(coordspace)):
        if (self.index < (len(self.manager) - 1)) and (numdimensions >= 0) and (numdimensions != len(coordspace)):
            raise AssertionError("Expected QR code %s count: %d (found %d)"%(dimension.name, numdimensions, len(coordspace))) 


    # OUT: pngpackage representing: coords(pngpackage)
    def getRegion(self, png, dimension, coords):
        w, h = png.getSize()
        img_cv2 = png.getImgCV2()
        if dimension == Dimension.qr:
            dimension = getInverted(Settings.first_dimension)#dimension.getFirstInverted()
        if dimension == Dimension.row: 
            n_tolerance = Settings.y_tolerance
            d1 = h
            d2 = w
        elif dimension == Dimension.col:      
            n_tolerance = Settings.x_tolerance
            d1 = w
            d2 = h
        else:
            raise ValueError("Invalid dimension specified: %s"%(dimension)) 

        n1 = max(0, (coords[0] - n_tolerance))
        n2 = min(d1, (coords[1] + n_tolerance))

        if dimension == Dimension.row:
            new_img_cv2 = img_cv2[n1:n2, 0:d2]   
        elif dimension == Dimension.col: 
            new_img_cv2 = img_cv2[0:d2, n1:n2]
        else:
            raise ValueError("Invalid dimension specified: %s"%(dimension)) 

        return PngUtils.PngWrapper(None, None, new_img_cv2)


    def decode(self, png, maxpayloadsize, dimensionlimit, inc, doDownsize):
        scanner = zbar.ImageScanner()
        scanner.parse_config('enable')
        candidates = []
        data = ""
        haveMaxPayload = False
        img = png.getImgPIL().convert('L')
        # Uncomment this and you should see QR code image windows popping up. Should be a single QR code per image.
        #img.show()

        
        #root = Tkinter.Tk()  # A root window for displaying objects
        # Convert the Image object into a TkPhoto object
        #tkimage = ImageTk.PhotoImage(png.getImgPIL())
        #Tkinter.Label(root, image=tkimage, text="Pooey", compound=Tkinter.CENTER).pack() # Put it in the display window
        #root.mainloop() # Start the GUI

        while True:
            # Do a scan using 'zbar':
            w, h = img.size  # w & h should be approx same, coz QR codes are square
           # print "Attempting to decode image '%s' scaled @ (%d, %d)"%(self.whoami(), w, h)
            raw = img.tostring()
            zbar_img = zbar.Image(w, h, 'Y800', raw)
            # Attempt QR code scan detection+decode
            scanner.scan(zbar_img)
            for symbol in zbar_img:
             #   print "Image '%s' scaled @ (%d, %d) contains payload of size: %d bytes"%(self.whoami(), w, h, len(symbol.data))
                candidates.append(symbol.data)
                if len(symbol.data) == maxpayloadsize:
                    haveMaxPayload = True 
        
            if haveMaxPayload:
                break

            # We wind up here if we are unsuccessful in our scan.
            # Resize the image and re-attempt.       
            if doDownsize:
                new_w = w - inc
                if (new_w < dimensionlimit):
                    break
            else: # upsize instead
                new_w = w + inc
                if (new_w > dimensionlimit):
                    break
            reduction_factor = (new_w / float(w))
            new_h = int((float(h) * float(reduction_factor)))
            img = img.resize((new_w, new_h), PIL.Image.ANTIALIAS)     
    
        for candidate in candidates:
            if len(candidate) > len(data):
                data = candidate

        return data




