import WorkerManager
import FilePathWrapper
import PngUtils
import FileUtils
import PIL
from PIL import Image
import cv2
import zbar
from WorkerManager import WorkerType
from WorkerManager import WorkerStatus
import Utils
import shutil
import FileHasher

#################################################################################################################

class Parameters(object):
 
    def __init__(self, input_fw, output_fw, minpayloadsize, maxpayloadsize, minimum_resize_dimension, maximum_resize_dimension, resize_increment, mask_list=None):
        self.input_fw = input_fw
        self.output_fw = output_fw
        self.minpayloadsize = minpayloadsize
        self.maxpayloadsize = maxpayloadsize       
        self.minimum_resize_dimension = minimum_resize_dimension
        self.maximum_resize_dimension = maximum_resize_dimension
        self.resize_increment = resize_increment
        self.mask_list = mask_list

    def getHash(self, algorithm):
        hasher = FileHasher.FileHasher(algorithm)
        hasher.addStr(str(self.minpayloadsize))
        hasher.addStr(str(self.maxpayloadsize))
        hasher.addStr(str(self.minimum_resize_dimension))
        hasher.addStr(str(self.maximum_resize_dimension))
        hasher.addStr(str(self.resize_increment))
        return hasher.getHash()
        
        
#################################################################################################################

class QRDecoder(WorkerManager.WorkerManager):

    def run(self, parameters):
                      
        # For each QR code in the input source set:
        i = 0
        l = parameters.input_fw.getSortedDirContents(True)
        for fw in l:

            if not i in parameters.mask_list: 
                qrcode = QRCode(self, fw, parameters.output_fw.getExtended("%s.txt"%(fw.getBasenameWoutExt())), parameters)
                # Schedule a worker:
                self.scheduleWorker(qrcode, qrcode.work) 

            i += 1 

        # Start the workers:
        self.startWorkers()

        # All workers complete without error?
        if not self.joinWorkers():
            # FIXME:
            raise QRCode.FatalDecodeError(str("SetManager:run(): fatal error raised"))

        
    # IN: 
    # input_fw:  <path to>/input/                                  <--- directory containing input QR code source files (they are assumed to be in order)
    # output_fw: <path to>/output/                                 <--- output directory 
    def __init__(self):
        # Invoke the super (WorkerManager.Worker) class constructor:
        super(QRDecoder, self).__init__(WorkerType.thread)      
        # FIXME: prolly wanna do some type of input sanitisation check:
        #self.input_fw = input_fw
       # self.output_fw = output_fw
        
 


#################################################################################################################


class QRCode(WorkerManager.Worker, WorkerManager.WorkerManager):


    # IN: 
    # fixme
    def __init__(self, manager, input_fw, output_fw, parameters):
        # Invoke the super (WorkerManager.Worker) class constructor:
        super(QRCode, self).__init__(manager)
        self.input_fw = input_fw
        self.output_fw = output_fw
        self.parameters = parameters
        


    def work(self, rtargs=None):
        self.prework()

        #print "Decoding: %s"%(self.input_fw.getBasenameWoutExt())

        status = WorkerStatus.completed_success

        png = PngUtils.PngWrapper(self.input_fw)

        data1 = self.decode(png, self.parameters.maxpayloadsize, self.parameters.minimum_resize_dimension, self.parameters.resize_increment, True) 
        if len(data1) < self.parameters.maxpayloadsize:
            # Suboptimal? Try instead applying a up-resize strategy:
            data2 = self.decode(png, self.parameters.maxpayloadsize, self.parameters.maximum_resize_dimension, self.parameters.resize_increment, False) 
            if (len(data1) > len(data2)):
                data = data1
            else:
                data = data2
        else:
            data = data1

        if len(data) >= self.parameters.minpayloadsize:
            #print "DECODE SUCCESS: %s (%s)"%(Utils.prettyPrint1(self.xml), Utils.prettyPrint2(self.xml))
            try:
                FileUtils.writeToFile(self.output_fw.getPath(), data)
             
            except IOError:
                #    print "Could not write: %s"%(data_fw.getPath())
                status = WorkerStatus.completed_fatal_error
                # FIXME : return me out of here!
        else:
            #print "Could not decode: %s"%(self.input_fw.getBasenameWoutExt())
            status = WorkerStatus.completed_not_successful


        # Finish work:   
        self.postwork(status)

    ###################################################################################################

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
            try:
                raw = img.tobytes()
            except SystemError:
                # Bad image... usually it's noise that is interpreted as a qr code
                return ""
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

