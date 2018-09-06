import XmlUtils
from lxml import etree as ElementTree
import Settings
import FilePathWrapper


# IN:
# input_fw : <path to>/input/
# 
# OUT:
# output_fw : <path to>/input/tag-n/
#
class XmlFileMap(object):

    def __len__(self):
        return len(self.xml)
 
    def __init__(self, input_fw, xmlroot, tag, hashval):
        self.exists = False
        xml = xmlroot.find("%s[@%s='%s']"%(tag, Settings.hash_attrib, hashval))
        if xml is None:
            # DNE.
            index = self.getNextIndex(xmlroot, tag)
            xml = XmlUtils.getOrAddChild(xmlroot, tag, {Settings.index_attrib:str(index), Settings.hash_attrib:hashval})    
        else:
            self.exists = True
            index = xml.get(Settings.index_attrib)
        self.output_fw = input_fw.getExtended("%s%s"%(tag, index))  
        self.xml = xml

        # If dir already exists, nothing happens.
        if not self.output_fw.createDir():
            raise Exception()


    # Gets the next AVAILABLE index
    def getNextIndex(self, xmlroot, tag):
        i = 0
        while xmlroot.find("%s[@%s='%s']"%(tag, Settings.index_attrib, str(i))) is not None:
             i += 1
        return i

