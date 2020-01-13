#!/bin/bash

for alg in {0..2}; do
	~/cst-iii-r244/graph_nets/graph_execute.py $alg $1 > results/graph_nets/$1_$alg 2> err/graph_nets/$1_$alg
done
