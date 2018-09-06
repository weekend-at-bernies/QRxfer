import sys
import FileHasher
import QuantizedInt
from Dimension import Dimension

#################################################################################################################

# Customizable globals

hashing_algorithm = "md5"           # Hashing algorithm for fingerprinting sessions/parameter sets/etc.
all_available_sets = False          # Attempt decoding against ALL .png sets (new and previous ones) 
dump_artefacts = True          

# .pdf conversion parameters
depth = 1
quality = 100
#density = QuantizedInt.QuantizedInt(300, 320, 10) #QuantizedInt.QuantizedInt(200, 210, 10) # density = (x, y, n)  which means, start at 'x', end at 'y', and increment by 'n' in between, so for example: (300, 320, 10) results in: 300, 310 & 320
density = QuantizedInt.QuantizedInt(300, 320, 10)

# QR decoding parameters (FIXME: possibly need to separate this into QR Extraction and QR Decoding)
maxpayloadsize = 2900              # Maximum size (in bytes) encodable by single QR code 
minpayloadsize = 10                # Minimum size (in bytes) encodable by single QR code 
x_tolerance = 3                   # Amount of tolerance/slack (in pixels) that is allowable around a single detected/extracted QR code
y_tolerance = 3
region_tolerance = 5               # Minimum region dimension (in pixels) in order to be considered as a possible QR code
expected_num_rows = -1             # Expected number of rows / QR code matrix (set to -1 otherwise this value is enforced)
expected_num_cols = -1             # Expected number of columns / QR code matrix (set to -1 otherwise this value is enforced)
minimum_resize_dimension = 400     # The minimum resizing dimension (in pixels) of a single QR code
maximum_resize_dimension = 1000    # The maximum resizing dimension (in pixels) of a single QR code
resize_increment = 5               # The amount by which we change the resize dimension variable
single_qrcode_filename = "qrcode"  # Single qrcode .png filename (without extension)
decoded_data_filename = "data.txt" # Decoded data filename
first_dimension = Dimension.row    # Which dimension to start processing QRcode matrices from

#### PHASE OUT ####
# Use these for fingerprinting (hashing) the QR decoding parameter set:
hashlist1 =  ['maxpayloadsize', 
              'minpayloadsize', 
              'x_tolerance', 
              'y_tolerance', 
              'region_tolerance', 
              'minimum_resize_dimension', 
              'maximum_resize_dimension', 
              'resize_increment', 
              'first_dimension']

# Use these for fingerprinting (hashing) the .png -> .pdf conversion parameter set:
hashlist2 = ['depth', 
             'quality', 
             'density']


#### PHASE IN ####

# Use these for fingerprinting (hashing) the QR extraction parameter set:
hashlist3 =  ['x_tolerance',  
              'y_tolerance',  
              'region_tolerance',  
              'first_dimension'] 

# Use these for fingerprinting (hashing) the QR decoding parameter set:
hashlist4 =  ['maxpayloadsize', 
              'minpayloadsize', 
              'minimum_resize_dimension', 
              'maximum_resize_dimension', 
              'resize_increment']

################

# XML configuration parameters
xml_config = "config.xml"             # XML configuration file (captures information for ALL projects)
project_tag = "project"               # <project>
hash_tag = "hash"                     # <hash>
src_tag = "src"                       # <src>
set_tag = "set"                       # <set>
decode_tag = "decode"                 # <decode>
merged_tag = "merged_input"         # <merged_input>
session_tag = "session"               # <session>
matrix_tag = "matrix"                 # <matrix>
row_tag = "row"                       # <row>
col_tag = "col"                       # <col>
qr_tag = "QR"                         # <QR>
result_tag = "result"                 # <result>
input_tag = "input"                   # YES
extract_tag = "extract"                   # YES
hash_attrib = "hash"
name_attrib = "name"       
index_attrib = "index"  
decoded_attrib = "decoded"
count_attrib = "count"      


# Used mostly by Dimension class QRCode.py ???
matrix_set = set_tag
matrix = matrix_tag         
row = row_tag     
col = col_tag                 
qr = qr_tag                           


# Directory names (use the xml tag names)
project = project_tag               # Input dir tag
decode = decode_tag                 # Decoding area dir tag
session = session_tag
src = src_tag                        # Decode input source
converted_pdf = matrix_tag          # Converted image filename representing matrix of QR codes

#################################################################################################################

# Util functions

def getHash(hasher, hashlist, index=0):
    for s in hashlist:
        attr = getattr(sys.modules[__name__], s)
        if isinstance(attr, str):
            hasher.addStr(attr)
        elif isinstance(attr, int):
            hasher.addStr("%d"%(attr))
        elif isinstance(attr, QuantizedInt.QuantizedInt):
            hasher.addStr("%d"%(attr.getVal(index)))
        else:
            hasher.addStr(str(attr))




