#!/usr/bin/python3
from random import randrange
import sys

fname = sys.argv[2]
nodes = int(sys.argv[1])

with open('%s' % (fname), 'w') as f:
    for i in range(nodes):
        for j in range(nodes):
            f.write("%d %d\n" % (i+1, j+1))
