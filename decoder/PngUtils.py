import PIL
from PIL import Image
import cv2
import zbar
import os
import sys
import FilePathWrapper

#################################################################################################################
# RGB TUPLE/TALLY FUNCTIONS

white_rgb = (255, 255, 255)
black_rgb = (0, 0, 0)

# IN: a list of RGB tuples like this: [(255, 255, 255), (30, 50, 300), ...]
# OUT: a dictionary which tallies the count of colours detected. For example,
#      the key (255, 255, 255) may return the value 60, which implies 'white' 
#      (which has RGB value: 255, 255, 255) was found 60 times in the input list.
def getRGBTally(rgb_list):
    rgb_tally = {}
    # Tally all the colours in the list
    for rgb in rgb_list:
        try:
            # Increment the colour if it's already in the tally:
            rgb_tally[rgb] += 1
        except KeyError:
            # Otherwise add the new colour to the tally:
            rgb_tally[rgb] = 1 
    return rgb_tally

# IN: 1) an input RGB tally (refer to getRGBTally())
#     2) supported_rgb_list: a list of the RGB tuples that the tally must ONLY support/contain (no others).
# OUT: True or False
def supportsRGBTally(rgb_tally, supported_rgb_list):
    rgb_tally_list = list(rgb_tally.keys())
    for rgb in rgb_tally_list:
        if rgb not in supported_rgb_list:
            return False
    return True
   

def getTotalRGBTally(rgb_tally):
    tally_keys = list(rgb_tally.keys())
    count = 0
    for key in tally_keys:
        count += rgb_tally[key]
    return count
    

# FIXME - right now just checking 100% white.
# What we want to check for is something like 99% uniformity of any one RGB combo
def containsAsPercentRGBTally(rgb_tally, rgb):
    try:
        rgb_count = rgb_tally[rgb]
    except KeyError:
        return 0
    return float(rgb_count) / float(getTotalRGBTally(rgb_tally))

#################################################################################################################

def doRowColChecks(rgb_tally):
    # B&W check:
    if supportsRGBTally(rgb_tally, [white_rgb, black_rgb]):
        return True
    return False

def containsMostlyWhite(rgb_tally, threshold=0.95):
    percent_white = containsAsPercentRGBTally(rgb_tally, white_rgb)
   # print "%f"%(percent_white)
    if percent_white > threshold:
        return True
    return False

# These filters out regions that probably aren't QR codes coz they're so small.
# EXAMPLE:
# IN : [[336, 1368], [1413, 2442], [2488, 3520], [3566, 4605], [4924, 4927]]
# OUT : [[336, 1368], [1413, 2442], [2488, 3520], [3566, 4605]]
def filterRegions(regions, tolerance):
    filteredRegions = []
    for region in regions:
        if (region[1] - region[0] >= tolerance):
            filteredRegions.append(region)
    return filteredRegions

#################################################################################################################

# Returns a list like this: [ [m1, n1], [m2, n2], [m3, n3], ... ]
# The sublists capture the target Y coordinate row spaces 
def getRows(rgb_image):
    width, height = rgb_image.size
    foundRegionStart = False
    targetRegions = []
    region = []
    rgb_tally = {}
    for y in range(0, height): 
        row = [rgb_image.getpixel((i, y)) for i in range(width)]
        rgb_tally = getRGBTally(row)
        if not doRowColChecks(rgb_tally):
            raise IOError("Image is not B&W")
        if containsMostlyWhite(rgb_tally):
            if foundRegionStart == True:
                # Found the end of a region
                foundRegionStart = False
                region.append(y - 1)
                targetRegions.append(region)
                region = []
        else:
            if foundRegionStart == False:
                # Found the start of a region
                foundRegionStart = True
                region.append(y)
    return targetRegions

# Returns a list like this: [ [m1, n1], [m2, n2], [m3, n3], ... ]
# The sublists capture the target X coordinate col spaces 
def getCols(rgb_image):
    width, height = rgb_image.size
    foundRegionStart = False
    targetRegions = []
    region = []
    rgb_tally = {}
    for x in range(0, width): 
        col = [rgb_image.getpixel((x, i)) for i in range(height)]
        rgb_tally = getRGBTally(col)
        if not doRowColChecks(rgb_tally):
            raise IOError("Image is not B&W")
        if containsMostlyWhite(rgb_tally):
            if foundRegionStart == True:
                # Found the end of a region
                foundRegionStart = False
                region.append(x - 1)
                targetRegions.append(region)
                region = []
        else:
            if foundRegionStart == False:
                # Found the start of a region
                foundRegionStart = True
                region.append(x)
    return targetRegions

#################################################################################################################

# A class that takes in: input png file (as fw) OR PIL image OR CV2 image
class PngWrapper(object):

    def __init__(self, img_fw, img_pil=None, img_cv2=None):
        self.img_fw = img_fw
        self.img_pil = img_pil
        self.img_cv2 = img_cv2

    def getFilePath(self):
        if self.img_fw != None:
            return self.img_fw.getPath()

    def getImgPIL(self):
        if self.img_pil != None:
            return self.img_pil
        elif self.img_fw != None:
            return Image.open(open(self.img_fw.getPath()))
        elif self.img_cv2 is not None:
            return Image.fromarray(self.img_cv2) 

    def getImgCV2(self):
        if self.img_cv2 is not None:
            return self.img_cv2
        elif self.img_fw != None:
            return cv2.imread(self.img_fw.getPath())
        elif self.img_pil != None:
            return cv2.cvtColor(numpy.array(self.img_pil), cv2.COLOR_RGB2BGR)

    def getSize(self):
        img_pil = self.getImgPIL()
        return img_pil.size 
        

