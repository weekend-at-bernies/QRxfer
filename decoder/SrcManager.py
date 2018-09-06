import subprocess
import sys
import os
import WorkerManager
import FilePathWrapper
from WorkerManager import WorkerType
from WorkerManager import WorkerStatus
import Settings
import FileHasher
#import SimpleXmlTree
#import xml.etree.ElementTree as ElementTree
import XmlUtils
import shutil as shutil

#################################################################################################################

class ConversionWorker(WorkerManager.Worker):

    # IN: args[density, depth, quality]
    #
    # density : .pdf conversion parameter
    # depth : .pdf conversion parameter
    # quality : .pdf conversion parameter
    #
    def work(self, rtargs):
        self.prework()

        self.density = self.args[0]
        self.depth = self.args[1]
        self.quality = self.args[2]
        status = WorkerStatus.completed_success
       
        try:
            s = subprocess.check_output(self.getConvertCmd2())
            if (len(s) > 0):
                #self.err = s
                status = WorkerStatus.completed_fatal_error
        except: # Catching all errors
            e = sys.exc_info()[0]
            #self.err = str(e)
            status = WorkerStatus.completed_fatal_error

        # Finish work:   
        self.postwork(status)

    # IN:
    # input_fw : <path to>/input.pdf
    # output_fw : <path to>/converted/          <--- output dir for converted .pdf files
    #
    def __init__(self, input_fw, output_fw):
        # Invoke the super (WorkerManager.Worker) class constructor:
        super(ConversionWorker, self).__init__()
        self.input_fw = input_fw
        self.output_fw = output_fw
        
    

    # As list
    def getConvertCmd2(self):
        # Throw in a "-type Grayscale" perhaps?
        l = []
        l.append("convert")
        l.append("-density")
        l.append("%d"%(self.density))
        l.append("-depth")
        l.append("%d"%(self.depth))
        l.append("-quality")
        l.append("%d"%(self.quality))
        l.append("%s"%(self.input_fw.getPath()))
        l.append("%s/%s.png"%(self.output_fw.getPath(), Settings.converted_pdf))
        return l

#################################################################################################################

class SrcManager(WorkerManager.WorkerManager):

    # IN:
    # input_fw  : <path to>/input                         <--- input file or directory
    # output_fw : <path to>/project/src/                  <--- dir where input source "sets" will be generated...
    #             <path to>/project/src/setx/                  ... in order like this
    #             <path to>/project/src/sety/     
    #             etc.
    # xml : xml src node
    def __init__(self, input_fw, output_fw, xml):
        super(SrcManager, self).__init__(WorkerType.thread)
        self.input_fw = input_fw
        self.output_fw = output_fw
        self.xml = xml
        self.density = Settings.density
        self.depth = Settings.depth
        self.quality = Settings.quality 
        self.targetsets = []

    def run(self):

        if self.input_fw.isExistingDir():
	    # The input is assumed to be a directory of ORDERED source files (single set), so this structure will be created:
            #
	    # <path to>/project/src/setx     <--- input source will be copied to here
            #  Where 'x' is the next available set index.

            # Generate input hash over input src:
            hasher = FileHasher.FileHasher(Settings.hashing_algorithm)
            srclist = []
	    for f in self.input_fw.getSortedDirContents():
		if (f.isExistingFile()) and (f.getExtension(False).lower() == "png"):
		    srclist.append(f.getPath())
	    hasher.addFile(srclist)
	    hashval = hasher.getHash()

            xmlset = self.xml.find("%s[@%s='%s']"%(Settings.set_tag, Settings.hash_attrib, hashval))
            if xmlset is None: 
                nextIndex = len(self.xml)
	        xmlset = XmlUtils.getOrAddChild(self.xml, Settings.set_tag, {Settings.index_attrib:"%d"%(nextIndex), Settings.hash_attrib:hashval})
                self.targetsets.append(xmlset)
                set_fw = self.output_fw.getExtended("%s%d"%(Settings.matrix_set, nextIndex))

                if not set_fw.createDir():
		    raise OSError("Error: could not create directory: %s"%(set_fw.getPath()))
                
                i = 0
		for f in srclist:
		    try:
		        shutil.copyfile(f, (set_fw.getExtended("%s-%d.png"%(Settings.converted_pdf, i)).getPath()))    
		    except:
		        raise Exception("Error: could not copy '%s' to: %s"%(f, set_fw.getExtended("%s-%d.png"%(Settings.converted_pdf, i)).getPath()))
                        # FIX ME: RAISE EXCEPTION INSTEAD
		    i += 1

            
 
        # Assert that input is a .pdf file
        # FIXME: is there a better check than just checking the extension???
        elif (self.input_fw.isExistingFile()) and (self.input_fw.getExtension() == ".pdf"):
            # The input is assumed to be a file that is required to be converted into source files (across multiple sets), so this structure will be created:  
            #                          
	    # <path to>/project/src/setx/      <--- converted files will be written here
	    # <path to>/project/src/sety/      <--- converted files will be written here
	    # <path to>/project/src/setz/      <--- converted files will be written here
	    #  etc.
	    #  Where 'x', 'y', 'z' are set indices incremented from the next available one.
            
	    i = 0
	    while self.density.inRange(i):
	    
	        # Generate input hash over input src file + conversion params:
                hasher = FileHasher.FileHasher(Settings.hashing_algorithm)
                hasher.addFile([self.input_fw.getPath()])
                Settings.getHash(hasher, Settings.hashlist2, i)
                hashval = hasher.getHash()

                xmlset = self.xml.find("%s[@%s='%s']"%(Settings.set_tag, Settings.hash_attrib, hashval))
                if xmlset is not None: 
		    # A converted set APPEARS (according to our xml config) to already exist.
		    # We'll just silently skip over then...
		    #print "Converted source set already exists: %s"%(hashval)
		    pass
		else:
                    # No converted set exists. We'll have to create one then.
                    nextIndex = len(self.xml)
                    xmlset = XmlUtils.getOrAddChild(self.xml, Settings.set_tag, {Settings.index_attrib:"%d"%(nextIndex), Settings.hash_attrib:hashval})
		    
		    set_fw = self.output_fw.getExtended("%s%d"%(Settings.matrix_set, nextIndex))
	        
                    # FIXME: is this check too much?
		    #if set_fw.isExistingDir():
		    #    raise Exception("Error: directory already exists: %s"%(set_fw.getPath()))
		                 
		    # Can't we get the workers to do this?
		    # Short answer: no. There seem to be not properly understood issues at play.
		    if not set_fw.createDir():
		        raise OSError("Error: could not create directory: %s"%(set_fw.getPath()))
		   
		    # Create a worker:
		    worker = ConversionWorker(self.input_fw, set_fw)
		    args = [self.density.getVal(i), self.depth, self.quality]

		    # Schedule the worker:
		    self.scheduleWorker(worker, worker.work, args)  
		                   
                self.targetsets.append(xmlset)
		i += 1
	   
            # Start the workers:
	    self.startWorkers()

	    if not self.joinWorkers():
	        raise AssertionError("Not all workers have completed succesfully!")
     
        else:
            # FIXME
            raise Exception("Invalid input: %s"%(self.input_fw.getPath()))

        # Possible sanity check: same number of .png in each src dir



