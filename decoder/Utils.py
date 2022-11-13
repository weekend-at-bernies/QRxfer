from lxml import etree as ElementTree
import Settings
import FileHasher
#import XmlUtils

############################################################################################################3

# This code is specific to QRDECODER

#
# IN: <merged_session>, <session>, <set>, <matrix>, <row>, <col>, <QR>
# Inspects below the elements listed above to see if its <QR> leaves
# all have the attribute 'result' set to '1'.
def isDecoded(e):
    if len(e) == 0:
        return False
    it = e.iter()
    while True:
        try:
            next_e = it.next()
            if next_e.tag == Settings.qr_tag:
                #if next_e.get(Settings.result_attrib) is None:
                #    return False
                #if not int(next_e.get(Settings.result_attrib)):
                #    return False
                if (next_e.text is not None) and (not int(next_e.text.strip())):
                    return False
                
        except StopIteration:
            break
    return True

# IN: preferably <merged_session>
def getDecodedCount(e):
    n = 0
    xmlqrs = getQRElements(e)
    for xmlqr in xmlqrs:
        if xmlqr.text == "1":
            n += 1 
    return n

# IN: preferably <merged_session>
def getQRCount(e):
    return len(getQRElements(e))

# IN: preferably <merged_session>
def getQRElements(e):
    l = []
    it = e.iter()
    while True:
        try:
            next_e = it.next()
            if next_e.tag == Settings.qr_tag:
                l.append(next_e)
        except StopIteration:
            break
    return l

# Call on: <matrix>, <row>, <col> or <QR>
# Returns (for example): "matrix-0 -> row-1 -> QR-4" 
def prettyPrint1(e):
    s = ""
    s += "%s-%s"%(e.tag, e.get(Settings.index_attrib))
    if e.tag != Settings.matrix_tag:
        s = prettyPrint1(e.getparent()) + " -> " + s
    return s

# Call on: <set>, <matrix>, <row>, <col> or <QR>
# Returns (for example): "set-3"
def prettyPrint2(e):
    s = ""
    if e.tag == Settings.set_tag:
        s += "%s-%s"%(e.tag, e.get(Settings.index_attrib))
    else:
        s += prettyPrint2(e.getparent())
    return s


def getIndexedStr(m, n):
    numdigits = len(str(n))
    s = str(m)
    while len(s) < numdigits:
        s = "0" + s
    return s


# not being used anymore, but pretty cool nonetheless
def getHash(obj, algorithm):
    hasher = FileHasher.FileHasher(algorithm)
    vl = obj.__dict__.keys()
    vl.sort()
    for v in vl:
        hasher.addStr(str(obj.__dict__[v]))
    return hasher.getHash()



