Developer's Notes
-----------------

Refer to: 'dev1.png' for a high level developer's overview of the QR decoding process.

An input .pdf (refer to 'test.pdf' for an example) is converted into multiple input .png sets.
The number of input sets generated depends on how the 'density' parameter is configured in 'Settings.py':

# .pdf conversion parameters
depth = 1
quality = 100
density = QuantizedInt.QuantizedInt(300, 320, 10)

Given the example configuration for 'density' as shown above, this will result in density values of: 300, 310 and 320.
This will result in 3 x .pdf->.png conversions, and hence 3 x input sets.

It is important to note that each input set is logically identical. The reason for generating multiple input sets is to 
maximize this program's ability to decode ALL the QR codes. A single .png set on its own is unlikely to yield 100% decoded
QR codes.

For each input .png set, the QR codes will be individually extracted, also according to parameters set out in 'Settings.py'.

Finally, the individual QR codes will be decoded. This happens sequentially, on a set-by-set basis, until all QR codes have
been decoded. The program will only attempt to decode a QR code when it detects that it hasn't been decoded within a previous
set.

 
