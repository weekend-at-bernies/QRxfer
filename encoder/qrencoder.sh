#!/bin/bash

# Verified for: Ubuntu 14.04 LTS
# Package dependencies:
# - qrencode
# - imagemagick

OUT_DIR="out"
OUT_FILE_NAME="qr_out"
CHUNK_SIZE=2900
CHUNK_FILE_NAME="chunk"
NUM_ROWS=3
NUM_COLS=2
INPUT_FILE=""
KEEP_BASE64_CHUNKS=0
INPUT_ERR=0
VERBOSE=0
DONTASKJUSTDO=0
PDFFILE="out.pdf"

function USAGE ()
{
  echo ""
  echo "QR Code file encoder"
  echo "--------------------"
  echo ""
  echo "Description:"
  echo "Takes an input file, base64 encodes it, splits it into chunks of $CHUNK_SIZE bytes,"
  echo "converts each one into a QR code, and finally mashes all the QR codes across multiple"
  echo "generated images, in addition to outputting a .pdf: $PDFFILE"
  echo ""
  echo "Usage:"
  echo "$ ./qrencoder.sh -i <input-file> [-o <output dir>] [-r <num rows>] [-c <num cols>] [-k]"
  echo ""
  echo "-i : input file to encode (required)"
  echo "-o : output directory (cannot already exist; defaults to: ./$OUT_DIR)"
  echo "-r : max number of rows of QR codes per image (default: 3)"
  echo "-c : max number of cols of QR codes per image (default: 2)"
  echo "-k : keep base64 chunks (default: false)"
  echo "-v : verbose (default: false)"
  echo "-x : don't ask, just do (default: false)"
  echo ""
}

function YESORNO()
{
  echo ""
  echo "Is this correct?"
  echo "(Y/N): "
  read yesorno
  if [ "$yesorno" == "Y" -o "$yesorno" == "y" -o "$yesorno" == "YES" -o "$yesorno" == "yes" ] ; then
    return 1
  fi
  return 0
}

# Parse command line options
while getopts "i:o:r:c:kvx" option
do
  case $option in
    x  ) DONTASKJUSTDO=1;;
    i  ) INPUT_FILE=$OPTARG;;
    o  ) OUT_DIR=$OPTARG;;
    r  ) NUM_ROWS=$OPTARG;;
    c  ) NUM_COLS=$OPTARG;;
    k  ) KEEP_BASE64_CHUNKS=1;;
    v  ) VERBOSE=1;;
    *  ) INPUT_ERR=1
  esac
done

if [ $INPUT_ERR == 1 ] ; then
   echo "Error: invalid argument provided!"
   USAGE
   exit
fi

if [ -z "$INPUT_FILE" ] ; then
  echo "Error: no input file provided!"
  USAGE
  exit
fi

if [ ! -e $INPUT_FILE ] ; then
  echo "Error: input file does not exist: $INPUT_FILE" 
  USAGE
  exit
fi

if [ -e ./$OUT_DIR ] ; then
  echo "Error: output directory already exists: ./$OUT_DIR"
  USAGE
  exit
fi

if [ $NUM_ROWS -le 0 ] ; then
  echo "Error: invalid number of rows specified: $NUM_ROWS"
  USAGE
  exit
fi

if [ $NUM_COLS -le 0 ] ; then
  echo "Error: invalid number of columns specified: $NUM_COLS"
  USAGE
  exit
fi

# Check 'convert' is available:
if [ -z `which convert` ] ; then
   echo "Error: missing 'convert' (is 'imagemagick' package installed?)"
   USAGE
   exit
fi

# Check 'qrencode' is available:
if [ -z `which qrencode` ] ; then
   echo "Error: missing 'qrencode' (is 'qrencode' package installed?)"
   USAGE
   exit
fi

# Make output/working directory
mkdir ./$OUT_DIR

if [ ! -e ./$OUT_DIR ] ; then
  echo "Error: could not create output directory: ./$OUT_DIR"
  USAGE
  exit
fi

if [ $VERBOSE == 1 ] ; then
   echo ""
   echo "Input file: $INPUT_FILE"
   echo "Output directory: $OUT_DIR"
   echo "Max number of rows of QR codes per image: $NUM_ROWS"
   echo "Max number of columns of QR codes per image: $NUM_COLS"
fi

if ! [ $DONTASKJUSTDO == 1 ] ; then
  YESORNO
  if [ $? -eq 0 ] ; then
    echo "Exiting..."
    exit
  fi
fi
echo ""

# Base64 encode the input file:
base64 $INPUT_FILE > ./$OUT_DIR/$INPUT_FILE.txt

# Split into chunks of specified number of bytes each.
split --bytes=$CHUNK_SIZE -d ./$OUT_DIR/$INPUT_FILE.txt ./$OUT_DIR/$CHUNK_FILE_NAME

# You might notice chunk number weirdness using 'split':
# ...
# chunk88
# chunk89
# chunk9000
# chunk90001
# ...
# Apparently it's OK, but if you don't like it, then refer to tips here:
# https://lists.gnu.org/archive/html/bug-coreutils/2015-06/msg00096.html

# Get the number of chunks:
NUM_CHUNKS=`ls -l ./$OUT_DIR | grep -v ^d | wc -l`
NUM_CHUNKS=$(( $NUM_CHUNKS-2 ))
# Each chunk will be encoded by a single QR code.
#echo "Number of QR codes required to encode input file: $NUM_CHUNKS"
echo "Total number of QR codes required: $NUM_CHUNKS"

QRCODES_PER_PNG=$(( $NUM_ROWS * $NUM_COLS ))
echo "Maximum number of QR codes per .png: $QRCODES_PER_PNG"

PNG_COUNT=$(( $NUM_CHUNKS / $QRCODES_PER_PNG ))
OVERFLOW=$(( $NUM_CHUNKS % $QRCODES_PER_PNG ))
if [ "$OVERFLOW" -gt 0 ] ; then
  PNG_COUNT=$(( $PNG_COUNT+1 ))
fi
echo "Total number of .png files required: $PNG_COUNT"


if ! [ $DONTASKJUSTDO == 1 ] ; then
  YESORNO
  if [ $? -eq 0 ] ; then
    echo "Exiting..."
    exit
  fi
fi 
echo ""

# FIXME: is there a max???? 
# Maximum allowable chunks is 1000: 'chunk000', 'chunk001', ..., 'chunk999'
#if [ "$NUM_CHUNKS" -gt 1000 ] ; then
#  echo "Error: number of chunks exceeds 1000"
#  USAGE
#  exit
#fi

# For each chunk, generate a QR Code .png image:
for f in ./$OUT_DIR/* ; do 
  if [ "$f" != "./$OUT_DIR/$INPUT_FILE.txt" ] ; then
    qrencode -o $f.png -t png < $f
    if [ $KEEP_BASE64_CHUNKS == 0 ] ; then
      rm $f
    fi
  fi
done

# Create our final .png images, each with $NUM_ROWS x $NUM_COLS QR codes.
# There may be remainder which we deal with afterwards.
PNG_COUNTER=1
COUNTER=0
ROW_COUNT=0
FINAL_COUNT=0
QRCODES_PER_PNG=$(( $NUM_ROWS * $NUM_COLS ))
CHUNK_LIST=""
CHUNK_COUNT=0
ROW_LIST=""
if [ $VERBOSE == 1 ] ; then
  echo "Max number of QR codes per generated image: $QRCODES_PER_PNG"
fi
echo ""
for f in ./$OUT_DIR/*.png ; do 

  PROGRESS_STR="Adding QR code: $f"
  if [ $VERBOSE == 1 ] ; then
    PROGRESS_STR="$PROGRESS_STR (destination: row $(( $ROW_COUNT+1 )), column $(( $CHUNK_COUNT+1 )))"
  fi
  echo "$PROGRESS_STR ..."

  # Create a row of $NUM_COLS QR codes:
  if [ $(( $(( COUNTER + 1 )) % $NUM_COLS )) -eq 0 ] && [ $COUNTER -ge 0 ] ; then
    convert +append $CHUNK_LIST $f ./$OUT_DIR/row$ROW_COUNT.png
    rm $CHUNK_LIST $f
    CHUNK_LIST=""
    CHUNK_COUNT=0
    ROW_LIST="$ROW_LIST./$OUT_DIR/row$ROW_COUNT.png "
    ROW_COUNT=$(( $ROW_COUNT+1 ))
    #if [ $VERBOSE == 1 ] ; then
    #  echo "  Completed row: $ROW_COUNT"
    #fi
  else
    CHUNK_LIST="$CHUNK_LIST$f "
    CHUNK_COUNT=$(( $CHUNK_COUNT+1 ))
  fi

  # Create a grid of $NUM_ROWS x $NUM_COLS QR codes:
  if [ $(( $(( COUNTER + 1 )) % $QRCODES_PER_PNG )) -eq 0 ] ; then
    if [ $COUNTER -ge 0 ] ; then
      echo "Generated $PNG_COUNTER of $PNG_COUNT: ./$OUT_DIR/$OUT_FILE_NAME$FINAL_COUNT.png (contains $QRCODES_PER_PNG QR Code(s))"
      if [ $VERBOSE == 1 ] ; then
        echo ""
      fi
      convert -append $ROW_LIST ./$OUT_DIR/$OUT_FILE_NAME$FINAL_COUNT.png
      FINAL_COUNT=$(( $FINAL_COUNT+1 ))
      ROW_COUNT=0
      rm $ROW_LIST
      ROW_LIST=""
      PNG_COUNTER=$(( $PNG_COUNTER+1 ))
    fi
  fi

  COUNTER=$(( $COUNTER+1 ))
done

REMAINS=""
REMAINS_COUNT=$(( $ROW_COUNT * $NUM_COLS + $CHUNK_COUNT ))

# Deal with any remainder rows (convert into incomplete matrix):
if [ ! -z "$ROW_LIST" ] ; then
  convert -append $ROW_LIST ./$OUT_DIR/row_remains.png
  rm $ROW_LIST
  ROW_LIST="" 
  ROW_COUNT=0
  REMAINS="./$OUT_DIR/row_remains.png "
fi

# Deal with any remainder chunks (convert into an incomplete row)
if [ ! -z "$CHUNK_LIST" ] ; then
  convert +append $CHUNK_LIST ./$OUT_DIR/chunk_remains.png
  rm $CHUNK_LIST
  CHUNK_LIST="" 
  CHUNK_COUNT=0
  REMAINS="$REMAINS./$OUT_DIR/chunk_remains.png"
fi

if [ ! -z "$REMAINS" ] ; then
  echo "Generated $PNG_COUNTER of $PNG_COUNT: ./$OUT_DIR/$OUT_FILE_NAME$FINAL_COUNT.png (contains $REMAINS_COUNT QR Code(s))"
  convert -append $REMAINS ./$OUT_DIR/$OUT_FILE_NAME$FINAL_COUNT.png
  FINAL_COUNT=$(( $FINAL_COUNT+1 ))
  rm $REMAINS
fi

# Generate the output .pdf:
echo ""
echo "Generating: $OUT_DIR/$PDFFILE"
echo ""
convert ./$OUT_DIR/*.png ./$OUT_DIR/$PDFFILE


