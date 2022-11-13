import subprocess
import sys
import os
import WorkerManager
import FilePathWrapper
from WorkerManager import WorkerType
from WorkerManager import WorkerStatus
import Utils
import shutil as shutil
import FileHasher

#################################################################################################################

class Parameters(object):
 
    # IN:
    # input_fw : (1) file (2) or directory
    # output_fw : directory 
    def __init__(self, input_fw, output_fw, depth, quality, density):
        self.input_fw = input_fw
        self.output_fw = output_fw
        self.depth = depth
        self.quality = quality
        self.density = density

    def getHash(self, algorithm):
        hasher = FileHasher.FileHasher(algorithm)
        if self.input_fw.isExistingDir():
            l = []
            for fw in self.input_fw.getSortedDirContents(True):
                l.append(fw.getPath())
            hasher.addFile(l)
        elif self.input_fw.isExistingFile():
            hasher.addFile([self.input_fw.getPath()])
            hasher.addStr(str(self.depth))
            hasher.addStr(str(self.quality))
            hasher.addStr(str(self.density))
        else:
            raise Exception("Error: fixme")
        return hasher.getHash()

#################################################################################################################

class Converter(object):

    # IN:
    # prefix : output filename prefix, where default is: converted-0, converted-1, etc.
    def __init__(self, prefix="converted"):
        # FIXME do some input sanitization, eg. "prefix" has to be purely alpha
        self.prefix = prefix

    
    def run(self, params):

        try:
            
            if params.input_fw.isExistingFile():

                s = subprocess.check_output(self.getConvertCmd(params))
                if (len(s) > 0):
                    #self.err = s
                    return False

                count = len(params.output_fw.getSortedDirContents(True))

                # Perform some name correction over "convert" utility's output, eg. "-0.png" should be "-00.png" if there > 10 input
                if count > 10:
                
                    for fw in params.output_fw.getSortedDirContents(True):             
                        basename = fw.getBasenameWoutExt()
                        n = basename[(basename.index('-') + 1):]              
                        new_fw = fw.getLeadingPathAsWrapper().getExtended("%s-%s.png"%(self.prefix, Utils.getIndexedStr(n, count)))
                        shutil.move(fw.getPath(), new_fw.getPath())


            elif params.input_fw.isExistingDir():
                i = 0
                count = len(params.input_fw.getSortedDirContents(True))
                for fw in params.input_fw.getSortedDirContents(True):
                    new_fw = params.output_fw.getExtended("%s-%s.png"%(self.prefix, Utils.getIndexedStr(i, (count - 1))))
                    shutil.copyfile(fw.getPath(), new_fw.getPath())   
                    i += 1
                         
        except: # Catching all errors
            e = sys.exc_info()[0]
            #self.err = str(e)
            return False

        return True


    def getConvertCmd(self, params):
        # Throw in a "-type Grayscale" perhaps?
        l = []
        l.append("convert")
        l.append("-density")
        l.append("%d"%(params.density))
        l.append("-depth")
        l.append("%d"%(params.depth))
        l.append("-quality")
        l.append("%d"%(params.quality))
        l.append("%s"%(params.input_fw.getPath()))
        l.append("%s/%s.png"%(params.output_fw.getPath(), self.prefix))
        return l
    


