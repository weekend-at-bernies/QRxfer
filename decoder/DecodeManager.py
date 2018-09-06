import WorkerManager
import FilePathWrapper
import QRCode
import PngUtils
import FileUtils
#import Utils
import Settings
#import SimpleXmlTree
#import XmlDecodeManager
from Dimension import Dimension
from WorkerManager import WorkerType
from WorkerManager import WorkerStatus
import XmlUtils
import Utils
import copy
import FileHasher
import Extract # experimental
import Decode # experimental

#################################################################################################################

# At runtime, there are 'n' instances of this (where 'n' is the number of input source sets used for decoding).
# RUN SEQUENTIALLY! NOT CONCURRENT! REASON: <fixme>
# Each SetManager instance in turn generates 'm' workers, where 'm' is the number of matrices per source set.
class SetManager(WorkerManager.WorkerManager):

    def run(self):
                      
        # For each matrix in the input source set:
        i = 0
        for fw in self.input_fw.getSortedDirContents():


            if len(self.xmlmerged) > 0:
                xmlmergedmatrix = self.xmlmerged.find("%s[@%s='%d']"%(Settings.matrix_tag, Settings.index_attrib, i))
                if xmlmergedmatrix is None:
                    # FIXME: getting here indicates current input set matrix count != expected.
                    # Raise a custom exception.
                    raise Exception
                if Utils.isDecoded(xmlmergedmatrix):
                    # DECODED ALREADY
                    #print "Already processed (skipping): %s"%(Utils.prettyPrint1(xmlmergedmatrix))
                    i += 1
                    continue
            else:
                xmlmergedmatrix = None

            xmlmatrix = XmlUtils.getOrAddChild(self.xmlset, Settings.matrix_tag, {Settings.index_attrib:str(i)})
              
            qrcode = QRCode.QRCode(self, PngUtils.PngWrapper(fw), self.output_fw, Dimension.matrix, xmlmergedmatrix, xmlmatrix)   
            # Schedule a worker:
            self.scheduleWorker(qrcode, qrcode.work) 

            i += 1 

        # Start the workers:
        self.startWorkers()

        # All workers complete without error?
        if not self.joinWorkers():
            # FIXME:
            raise QRCode.FatalDecodeError(str("SetManager:run(): fatal error raised"))

        # First time run there will be no merged session branch so create it now by copying the first session run branch:
        if len(self.xmlmerged) == 0:
            for worker in self:        
                self.xmlmerged.append(copy.deepcopy(worker.xml))

        
    # IN: 
    # input_fw:  <path to>/src/setX/                                  <--- source dir (exists) 
    # output_fw: <path to>/decode/sessionY/setX/                      <--- output decoding directory (new)
    # xmlmerged: <merged_session>  
    # xmlset: <set>
    def __init__(self, input_fw, output_fw, xmlmerged, xmlset):
        # Invoke the super (WorkerManager.Worker) class constructor:
        super(SetManager, self).__init__(WorkerType.thread)      
        self.input_fw = input_fw
        self.output_fw = output_fw
        self.xmlmerged = xmlmerged
        self.xmlset = xmlset
        

#################################################################################################################

# At runtime, there should only be 1 instance of this.
class SessionManager(object):

    # IN: 
    # input_fw: <path to>/src/                          <--- source dir  
    #                 .../src/set1/                          (where the source sub-dirs reside)
    #                 .../src/set2/
    #                 etc.
    # output_fw: <path to>/decode                       <--- output decoding directory
    #                  .../decode/session1/                  ... where the decode session sub-dirs will be written
    #                  .../decode/session1/set1/             ... targetting the src sets above
    #                  .../decode/session1/set2/                  
    #                  .../decode/session2/
    #                  .../decode/session2/set1/           
    #                  .../decode/session2/set2/   
    #                  etc.   
    # src_indices: [n0, n1, n2, ... ]                        <--- source set indices (use these for decoding) 
    #                                                             (eg. if it were [0, 3, 5] then we'd use:
    #                                                                                       .../src/set0/                          
    #                                                                                       .../src/set3/
    #                                                                                       .../src/set5/
    #
    # xml : <decode> xml node
    def __init__(self, srcmanager, output_fw, xml):
        self.srcmanager = srcmanager
        self.output_fw = output_fw      
        self.xml = xml
            


    def run(self):


#############################

        for target in self.srcmanager.targetsets:
            i = target.get(Settings.index_attrib)

            srcset = "%s%s"%(Settings.matrix_set, i)
            input_fw = self.srcmanager.output_fw.getExtended("%s"%(srcset))
            output_fw = self.output_fw.getExtended("%s/%s"%(Settings.session, srcset))

            # FIXME: can't we get the workers to do this?
            if not output_fw.createDir():
                raise OSError("Error: could not create directory: %s"%(output_fw.getPath()))

            extract_params = Extract.Parameters(Settings.x_tolerance, Settings.y_tolerance, Settings.region_tolerance, Settings.first_dimension)
            test = Extract.QRExtractor(input_fw, output_fw)
            extractcount = test.run(extract_params)
            print "%d QRs extracted"%(extractcount)

            decode_params = Decode.Parameters(Settings.maxpayloadsize, Settings.minpayloadsize, Settings.minimum_resize_dimension, Settings.maximum_resize_dimension, Settings.resize_increment)
            test2 = Decode.QRDecoder(output_fw, FilePathWrapper.FilePathWrapper("/tmp/jeremy"))
            test2.run(decode_params)

            exit(-1)










############################


        # Get merged sessions (if available):
        xmlmerged = XmlUtils.getOrAddChild(self.xml, Settings.merged_tag)
        
        # Get hash over the decode args (the "session" hash):
        hasher = FileHasher.FileHasher(Settings.hashing_algorithm)
        Settings.getHash(hasher, Settings.hashlist1, 0)
        hashval = hasher.getHash()

        # Get a previous existing session or create a new one.
        # NOTE: getting a previous existing session is OK, because we might have new source sets with which to attempt decoding.
        xmlsession = XmlUtils.getOrAddChild(self.xml, Settings.session_tag, {Settings.hash_attrib:hashval})
        index = xmlsession.get(Settings.index_attrib)
        if index is None:
            index = len(self.xml) - 2
            xmlsession.set(Settings.index_attrib, str(index))
        else:
            index = int(index)
            #print "Found previous session..."

            s = ""
            s += "\nPREVIOUS SESSION\n"
            s += "----------------\n"
            s += "QR count: %d\n"%(Utils.getQRCount(xmlmerged))
            s += "Decoded total: %d\n"%(Utils.getDecodedCount(xmlmerged))
            s += "Decoded remaining: %d"%(Utils.getQRCount(xmlmerged) - Utils.getDecodedCount(xmlmerged))

            print s

        
        i2 = 0

        # FIXME: also need a way to get ALL available sets, not just the targets (Settings option)
        # For each target source set:
        for target in self.srcmanager.targetsets:
 
            i = target.get(Settings.index_attrib)

            # Have we already attempted to decode this source set?
            xmlset = xmlsession.find("%s[@%s='%s']"%(Settings.set_tag, Settings.index_attrib, i))
            if xmlset is not None:
                # Yes. Skip it.
                i2 += 1
                continue
            else:
                # No. Schedule it.
                xmlset = XmlUtils.getOrAddChild(xmlsession, Settings.set_tag, {Settings.index_attrib:i})

                   
            srcset = "%s%s"%(Settings.matrix_set, i)
            input_fw = self.srcmanager.output_fw.getExtended("%s"%(srcset))
            output_fw = self.output_fw.getExtended("%s%s/%s"%(Settings.session, index, srcset))

            # FIXME: can't we get the workers to do this?
            if not output_fw.createDir():
                raise OSError("Error: could not create directory: %s"%(output_fw.getPath()))


            prevDecodeCount = Utils.getDecodedCount(xmlmerged)
            
            # Create a setmanager instance:
            setManager = SetManager(input_fw, output_fw, xmlmerged, xmlset)
            setManager.run()

            currDecodeCount = Utils.getDecodedCount(xmlmerged)
            qrCount = Utils.getQRCount(xmlmerged)


            s = ""
            s += "\nPASS %d\n"%(i2 + 1)
            s += "---------\n"
            s += "QR count: %d\n"%(qrCount)
            s += "Decoded now: %d\n"%(currDecodeCount - prevDecodeCount)
            s += "Decoded total: %d\n"%(currDecodeCount)
            s += "Decoded remaining: %d"%(qrCount - currDecodeCount)

            print s
 
            i2 += 1

            

            

            
        






