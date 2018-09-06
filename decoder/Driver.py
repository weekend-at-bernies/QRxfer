# On Ubuntu 18.04 LTS, did this to resolve required dependencies (IN ORDER):
#
# $ pip install pillow                                      <--- pip version 8.1.1, however version 18.0 is available
# $ sudo apt-get install python-opencv libzbar-dev zbar-tools
# $ pip install zbar
#
# OTHER DEPENDENCIES:
# WorkerManager.pyc
# FilePathWrapper.pyc


#!/usr/bin/python

import sys
import os
import optparse
import shutil
import FilePathWrapper
import SrcManager
import FileHasher
import DecodeManager
import FileUtils
from lxml import etree as ElementTree
import Settings
import XmlUtils
import Utils
import base64

import MultiHandler
import Convert
import Extract
import Decode
import XmlFileMap

from WorkerManager import WorkerStatus
from WorkerManager import WorkerType
 
#################################################################################################################
# COMMAND LINE ARGUMENT PARSER

if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("-i", help="input .pdf file OR directory containing .png files (mandatory)", dest="inputtarget",  metavar="<inputtarget>")
    parser.add_option("-o", help="output directory (mandatory)", dest="outputdir",  metavar="<outputdir>")
    parser.add_option("-v", help="verbose", action="store_true", dest="verbose",  default=False)
    parser.add_option("-x", help="don't ask (just do)", action="store_true", dest="dontask",  default=False)
    (opts, args) = parser.parse_args()

Settings.verbose = opts.verbose

#################################################################################################################
# CHECK USER INPUT

if (opts.inputtarget is None) or (len(opts.inputtarget) == 0):
    print "Error: no input specified\n"
    parser.print_help()
    exit(-1)
else:
    input_fw = FilePathWrapper.FilePathWrapper(opts.inputtarget)

if (opts.outputdir is None) or (len(opts.outputdir) == 0):
    print "Error: no output directory specified\n"
    parser.print_help()
    exit(-1)
else:
    output_fw = FilePathWrapper.FilePathWrapper(opts.outputdir)

#################################################################################################################
# END-USER SANITY CHECK

if input_fw.isExistingFile():
    print "\nInput file: %s"%(input_fw)
elif input_fw.isExistingDir():
    print "\nInput directory: %s"%(input_fw)
else:
    print "Error: input could not be found: %s"%(input_fw)
    parser.print_help()
    exit(-1)

print "Output directory: %s"%(output_fw)
if output_fw.exists():
    if output_fw.isExistingDir():
        print "\nWARNING: output directory already exists!"
    else:
        print "Error: existing output not valid: %s"%(output_fw)
        parser.print_help()
        exit(-1)
 
if (opts.dontask is False):   
    print ""
    response = raw_input("Is this correct? (y/n): ")
    if (not response.upper() == 'Y'):
        print ""
        print "Exiting!"
        exit(0)
    
print ""
print "Starting..."

#################################################################################################################
# CREATE PROJECTS DIRECTORY AND XML CONFIG FILE

outbin_fw = output_fw.getExtended("out.bin") 
decodeout_fw = output_fw.getExtended("merged") 
xml_config_fw = output_fw.getExtended(Settings.xml_config) 

# Does <path to>/project/ exist?
if not output_fw.exists():
    # No. Create it.
    if not decodeout_fw.createDir():
        print "Error: could not create directory: %s"%(decodeout_fw)
        exit(-1)

# Does xml config file exists?   
if xml_config_fw.isExistingFile():
    # Yes. Open it. 
    et = ElementTree.parse(xml_config_fw.getPath()) 
    xmlroot = et.getroot()
else:
    # No. Create it.
    xmlroot = ElementTree.Element(Settings.project_tag)
    et = ElementTree.ElementTree(xmlroot)  

#################################################################################################################
# ACQUAINT OURSELVES WITH PREVIOUS SESSION DATA

xmlmerged = XmlUtils.getOrAddChild(xmlroot, Settings.merged_tag)
target_qr_count = -1
prev_decoded_qr_count = 0
if len(xmlmerged) > 0:

    print ""
    print "Previous session detected..."

    # At this stage, all subsequent input have to contain this many QR codes (for consistency):
    xmlqrcount = xmlmerged.find("%s[@%s]"%(Settings.qr_tag, Settings.count_attrib))
    if xmlqrcount is not None:      
        target_qr_count = int(xmlqrcount.get(Settings.count_attrib))
        print "  QR count: %d"%(target_qr_count)        
    else:
        print "Error: invalid config file: %s"%(xml_config_fw)
        exit(-1)

    #if len(xmlmerged) == 1:
    #    print "Error: input already decoded: %s"%(input_fw)
    #    exit(-1)

    prev_decoded_qr_count = len(decodeout_fw.getSortedDirContents(True))

    print "  Decoded QR count: %d"%(prev_decoded_qr_count)
    print "  Remaining count: %d"%(target_qr_count - prev_decoded_qr_count)
    
    if target_qr_count == prev_decoded_qr_count:
        print "  Decoded binary: %s"%(outbin_fw)
        print ""
        exit(-1)

#################################################################################################################
# CONVERT INPUT (multi-threaded)

params = []
xmlfilemap_list = []

# Generate input parameters:
if input_fw.isExistingDir():
    params.append(Convert.Parameters(input_fw, None, 0, 0, 0))
else:
    for density in Settings.density:
        params.append(Convert.Parameters(input_fw, None, Settings.depth, Settings.quality, density))

for p in list(params):
    try:
        xmlfilemap = XmlFileMap.XmlFileMap(output_fw, xmlroot, Settings.input_tag, p.getHash(Settings.hashing_algorithm))
    except Exception:
        # FIX ME : error message 
        exit(-1)

    if len(xmlfilemap) == 0:
        p.output_fw = xmlfilemap.output_fw  
    else:
       # print "Input set already exists: %s"%(xmlfilemap.output_fw)
        params.remove(p) 
               
    xmlfilemap_list.append(xmlfilemap)


if len(params) > 0:
    sys.stdout.write("\nGenerating %d input set(s)... "%(len(params)))
    sys.stdout.flush()
    multihandler = MultiHandler.Manager(WorkerType.process, Convert.Converter(Settings.converted_pdf))
    multihandler.run(params)
    print "%f seconds!"%(multihandler.getDuration())

#################################################################################################################
# EXTRACT QR CODES (multi-threaded)

params = []
old_xmlfilemap_list = xmlfilemap_list
xmlfilemap_list = []

for old_xmlfilemap in old_xmlfilemap_list:
      
    p = Extract.Parameters(None, None, Settings.x_tolerance, Settings.y_tolerance, Settings.region_tolerance, Settings.first_dimension)

    try:
        xmlfilemap = XmlFileMap.XmlFileMap(old_xmlfilemap.output_fw, old_xmlfilemap.xml, Settings.extract_tag, p.getHash(Settings.hashing_algorithm))
    except Exception:
        exit(-1)

    if len(xmlfilemap) == 0:
        p.input_fw = old_xmlfilemap.output_fw
        p.output_fw = xmlfilemap.output_fw
        params.append(p)
    else:
       # print "QR codes already extracted from input set: %s"%(xmlfilemap.output_fw)
        pass

    xmlfilemap_list.append(xmlfilemap)

if len(params) > 0:
    sys.stdout.write("\nExtracting QR codes from %d input set(s)... "%(len(params)))
    sys.stdout.flush()
    multihandler = MultiHandler.Manager(WorkerType.process, Extract.QRExtractor())
    multihandler.run(params)
    print "%f seconds!"%(multihandler.getDuration())

#################################################################################################################
# DECODE QR CODES (sequentially, not multi-threaded)


old_xmlfilemap_list = xmlfilemap_list

for old_xmlfilemap in old_xmlfilemap_list:

    curr_decode_count = len(decodeout_fw.getSortedDirContents(True))
    if curr_decode_count == target_qr_count:
        # All QR codes decoded; no need to proceed with further decoding
        break

    # QR CODE COUNT VERIFICATION
    qr_count = len(old_xmlfilemap.output_fw.getSortedDirContents(True))

    if target_qr_count < 0:
        print "  QR code count per set: %d"%(qr_count)
        target_qr_count = qr_count
        xmlqrcount = XmlUtils.getOrAddChild(xmlmerged, Settings.qr_tag, {Settings.count_attrib:"%d"%(qr_count)})
        for i in range(0, qr_count):
            xmlqr = XmlUtils.getOrAddChild(xmlmerged, Settings.qr_tag, {Settings.index_attrib:"%d"%(i)})
    else:
        if (qr_count != target_qr_count):
            print "Bad extraction set detected, should be %d extracted QR codes but got %d instead (skipping)..."%(target_qr_count, qr_count)
            continue

    mask_list = []

    for i in range(0, qr_count):
        if xmlmerged.find("%s[@%s='%d']"%(Settings.qr_tag, Settings.index_attrib, i)) is None:
            mask_list.append(i)
            
    p = Decode.Parameters(None, None, Settings.minpayloadsize, Settings.maxpayloadsize, Settings.minimum_resize_dimension, Settings.maximum_resize_dimension, Settings.resize_increment, mask_list)

    try:
        xmlfilemap = XmlFileMap.XmlFileMap(old_xmlfilemap.output_fw, old_xmlfilemap.xml, Settings.decode_tag, p.getHash(Settings.hashing_algorithm))
    except Exception:
        exit(-1)

    if xmlfilemap.exists:
        #print "QR codes already decoded from input set: %s"%(xmlfilemap.output_fw)
        pass
    else:
        p.input_fw = old_xmlfilemap.output_fw
        p.output_fw = xmlfilemap.output_fw

        sys.stdout.write("\nAttempting input set %d... "%(old_xmlfilemap_list.index(old_xmlfilemap) + 1))
        sys.stdout.flush()
        decode = Decode.QRDecoder()
        decode.run(p)    
        print "%f seconds!"%(decode.getDuration())

        decoded_qrs = p.output_fw.getSortedDirContents(True)
        for decoded_qr in decoded_qrs:
            target_index = int(decoded_qr.getBasenameWoutExt()[2:])         
            xmlqr = xmlmerged.find("%s[@%s='%d']"%(Settings.qr_tag, Settings.index_attrib, target_index))
            if xmlqr is not None:
                print "  Decoded QR %d"%(target_index)
                xmlmerged.remove(xmlqr)     
                shutil.copy(decoded_qr.getPath(), decodeout_fw.getPath())
            else:
                # Should NOT be getting here because it means we have been decoding QR codes that have already been decoded!
                print "QR %d was already decoded! Shouldn't have arrived here"%(target_index)

#################################################################################################################
# FINALIZE PROJECT (ONLY IF ALL QRS DECODED)

decode_fws = decodeout_fw.getSortedDirContents(True)
curr_decode_count = len(decode_fws)
if curr_decode_count == target_qr_count:     
    sys.stdout.write("\nFinalizing... ")
    sys.stdout.flush()
    strdata = ""
    for decode_fw in decode_fws:
        with open(decode_fw.getPath(), 'r') as f:
            strdata += f.read()
        f.close()

    base64_success = True
    try:
        decodeddata = base64.b64decode(strdata)
    except TypeError:
        #print "Error: base64 decoding error"
        #exit(-1)
        base64_success = False
     
    if base64_success:
        print "success!"
        f = open(outbin_fw.getPath(), "wb")
        f.write(decodeddata)
        f.close()
    else:
        print "failed!"

#################################################################################################################

print "\nSession complete..."
print "  QR count: %d"%(target_qr_count)
print "  Previously decoded: %d"%(prev_decoded_qr_count)
print "  Decoded during this session: %d"%(curr_decode_count - prev_decoded_qr_count)
print "  Remaining count: %d"%(target_qr_count - curr_decode_count)
if outbin_fw.isExistingFile():
    print "  Decoded binary: %s"%(outbin_fw)

        
FileUtils.writeToFile(xml_config_fw.getPath(), XmlUtils.dump(xmlroot, 4))

exit(0)















    







