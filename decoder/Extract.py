import WorkerManager
import FilePathWrapper
import PngUtils
import cv2
from Dimension import Dimension
from Dimension import getInverted
from WorkerManager import WorkerType
from WorkerManager import WorkerStatus
import Utils
import shutil
import FileHasher

#################################################################################################################

class Parameters(object):
 
    def __init__(self, input_fw, output_fw, x_tolerance, y_tolerance, region_tolerance, first_dimension):
        self.input_fw = input_fw
        self.output_fw = output_fw
        self.x_tolerance = x_tolerance
        self.y_tolerance = y_tolerance
        self.region_tolerance = region_tolerance
        self.first_dimension = first_dimension

    def getHash(self, algorithm):
        #return Utils.getHash(self, algorithm)
        hasher = FileHasher.FileHasher(algorithm)
        hasher.addStr(str(self.x_tolerance))
        hasher.addStr(str(self.y_tolerance))
        hasher.addStr(str(self.region_tolerance))
        hasher.addStr(str(self.first_dimension))
        return hasher.getHash()
        
#################################################################################################################

class QRExtractor(WorkerManager.WorkerManager):

    def run(self, parameters):
                      
        # For each matrix in the input source set:
        i = 0
        l = parameters.input_fw.getSortedDirContents(True)
        for fw in l:
             
            qrcode = QRCode(self, PngUtils.PngWrapper(fw), parameters.output_fw.getExtended("%s%s.png"%(str(Dimension.matrix), Utils.getIndexedStr(i, (len(l) - 1)))), Dimension.matrix, parameters)
            # Schedule a worker:
            self.scheduleWorker(qrcode, qrcode.work) 

            i += 1 

        # Start the workers:
        self.startWorkers()

        # All workers complete without error?
        if not self.joinWorkers():
            # FIXME:
            raise QRCode.FatalDecodeError(str("SetManager:run(): fatal error raised"))



        i = 0
        l = parameters.output_fw.getSortedDirContents(True)
        qrcount = len(l)
        for fw in l:
            # Beware the artefacts
            #print "%s"%(fw.getBasenameWoutExt())
            new_fw = parameters.output_fw.getExtended("%s%s.png"%(self.prefix, Utils.getIndexedStr(i, (len(l) - 1))))
            
            shutil.move(fw.getPath(), new_fw.getPath())
            i += 1
        return qrcount

        
    # IN: 
    # input_fw:  <path to>/input/                                  <--- directory containing input QR code matrix source files (they are assumed to be in order)
    # output_fw: <path to>/output/                                 <--- output directory <path to>/extract/
    def __init__(self, prefix="QR"):
        # Invoke the super (WorkerManager.Worker) class constructor:
        super(QRExtractor, self).__init__(WorkerType.thread)      
        # FIXME: prolly wanna do some type of input sanitisation check:
        self.prefix = prefix
        #self.input_fw = input_fw
       # self.output_fw = output_fw
      #  self.artefacts_fw = artefacts_fw
      #  self.parameters = parameters
        
 


#################################################################################################################

# This describes QRCodes in the following forms:
# Matrix of QRCodes
# Row of QRcode(s)
# Column of QRCode(s)
class QRCode(WorkerManager.Worker, WorkerManager.WorkerManager):


    # IN: 
    # png: png package wrapper around target QR code(s)
    # output_fw: <path to>/decode/attemptY/setX/ [matrixA/rowB/qrC/]                 <--- where the extracted png will be output
    # dimension: dimension of the current pngpackage (matrix, row/col or single QR code)
    def __init__(self, manager, png, output_fw, dimension, parameters):
        # Invoke the super (WorkerManager.Worker) class constructor:
        super(QRCode, self).__init__(manager)
        self.png = png
        self.output_fw = output_fw
        self.dimension = dimension 
        self.parameters = parameters
        


    def work(self, rtargs=None):
        self.prework()

        status = WorkerStatus.completed_success

       # print "Analyzing: %s (%s)"%(Utils.prettyPrint1(self.xml), Utils.prettyPrint2(self.xml))
       # print "Analyzing: %s"%(self.output_fw.getBasenameWoutExt())

        # Get nextdimension
        nextdimension = self.dimension.next()


        ###################################################################################################

        # PROCESSING A MATRIX OF QR CODES:
        if nextdimension != None:              

            

            basename = self.output_fw.getBasenameWoutExt()
            baseoutput_fw = self.output_fw.getLeadingPathAsWrapper()
            


            coordspace = self.getCoordSpace(self.png, self.parameters.region_tolerance, nextdimension)

            i = 0
            for coords in coordspace:


                nextpng = self.getRegion(self.png, nextdimension, coords)
                nextoutput_fw = baseoutput_fw.getExtended("%s_%s%s.png"%(basename, str(nextdimension), Utils.getIndexedStr(i, (len(coordspace) - 1))))


                

                qrcode = QRCode(self, nextpng, nextoutput_fw, nextdimension, self.parameters)

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
           # print "Writing: %s"%(self.output_fw.getPath())
            cv2.imwrite(self.output_fw.getPath(), self.png.getImgCV2())
            

        ###################################################################################################
            


        # Finish work:   
        self.postwork(status)

    ###################################################################################################

    def getCoordSpace(self, png, tolerance, dimension):  
        img_rgb = png.getImgPIL().convert('RGB')    
        if dimension == Dimension.qr:
            dimension = getInverted(self.parameters.first_dimension) 
        if dimension == Dimension.row: 
            coordspace = PngUtils.filterRegions(PngUtils.getRows(img_rgb), tolerance)   
        elif dimension == Dimension.col:
            coordspace = PngUtils.filterRegions(PngUtils.getCols(img_rgb), tolerance)
        else:
            raise ValueError("Invalid dimension specified: %s"%(dimension))
        return coordspace




    # OUT: pngpackage representing: coords(pngpackage)
    def getRegion(self, png, dimension, coords):
        w, h = png.getSize()
        img_cv2 = png.getImgCV2()
        if dimension == Dimension.qr:
            dimension = getInverted(self.parameters.first_dimension)
        if dimension == Dimension.row: 
            n_tolerance = self.parameters.y_tolerance
            d1 = h
            d2 = w
        elif dimension == Dimension.col:      
            n_tolerance = self.parameters.x_tolerance
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
