import Settings
from enum import Enum

def getDimension(s):
    if (s == Settings.matrix_set):
        return Dimension.matrix_set
    elif (s == Settings.matrix):
        return Dimension.matrix
    elif (s == Settings.row):
        return Dimension.row
    elif (s == Settings.col):
        return Dimension.col
    elif (s == Settings.qr):
        return Dimension.qr
    else:
        return None 

def getInverted(self):
    if (self == Dimension.row):
        return Dimension.col
    elif (self == Dimension.col):
        return Dimension.row
    else:
        return None

class Dimension(Enum):
    matrix_set = 0
    matrix = 1
    row = 2
    col = 3
    qr = 4

    def __str__(self):
        if (self == Dimension.matrix_set):
            return Settings.matrix_set
        elif (self == Dimension.matrix):
            return Settings.matrix
        elif (self == Dimension.row):
            return Settings.row
        elif (self == Dimension.col):
            return Settings.col       
        elif (self == Dimension.qr):
            return Settings.qr
        else:
            return None 

    def next(self):
        if (self == Dimension.matrix_set):
            return Dimension.matrix
        elif (self == Dimension.matrix):
            return Settings.first_dimension
        elif (self == Settings.first_dimension):
            return Dimension.qr
        else:
            return None


    

    
