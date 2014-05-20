#!/usr/bin/python

import sys
import re
from glob import glob
import numpy as np

png_files = glob( sys.argv[1] + "/*")
output_file = sys.argv[2]

boxes = {}
for f in png_files:
    pattern =  r'(?P<raw_file>[^/]+\.nii\.gz)_(?P<z>\d+)_(?P<y>\d+)_(?P<x>\d+)_(?P<d>\d+)_(?P<h>\d+)_(?P<w>\d+)\.png$'
    match = re.search( pattern, f )
    if match is None:
        raise ValueError( "Cannot parse: " + f )
    m = match.groupdict()
    boxes[m['raw_file']] = { 'c' : np.array([int(m['z']),
                                             int(m['y']),
                                             int(m['x'])], dtype=int),
                             's' : np.array([int(m['d']),
                                             int(m['h']),
                                             int(m['w'])], dtype=int) }

out = open(output_file,"w")
for f in boxes.keys():
    out.write( f + "\t"
               + ','.join( map( str, boxes[f]['c']) ) + ','
               + ','.join( map( str, boxes[f]['c']) ) )
    out.write("\n")

out.close()
