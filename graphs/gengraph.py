#!/usr/bin/python3
from random import randrange
import sys

fname = sys.argv[3]
nodes = int(sys.argv[1])
edges = int(sys.argv[2])

with open('%s' % (fname), 'w') as f:
    for i in range(edges):
        f.write("%d %d\n" % (randrange(1,nodes+1),randrange(1, nodes+1)))
