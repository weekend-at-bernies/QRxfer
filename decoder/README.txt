How to run the test:

$ cp test.pdf /tmp
$ rm -rf /tmp/bif
$ python Driver.py -i /tmp/test.pdf -o /tmp/bif -v

TO DO:
- Implement better verbosity via: -v
- Check if FilePathWrapper is REALLY necessary
- Verify these:
  expected_num_rows = -1             # Expected number of rows / QR code matrix (set to -1 otherwise this value is enforced)
  expected_num_cols = -1 
