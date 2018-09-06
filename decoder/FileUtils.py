import os
import sys



def writeToFile(filename, data):
    with open(filename, 'w') as f:
        f.write(data)
        f.flush()
        os.fsync(f)
        f.close()

# Append filename2 to filename1
def appendToFile(filename1, filename2):
    f1 = open(filename1, 'a+')
    f2 = open(filename2, 'r')
    f1.write(f2.read())
    f1.flush()
    os.fsync(f1)
    f1.close()
    f2.close()
