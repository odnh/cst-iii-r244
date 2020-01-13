#!/bin/bash
export GRAPHCHI_ROOT=~/graphchi-cpp

for alg in "pagerank" "singlesourceshortestpath" "connectedcomponents"; do
	~/graphchi-cpp/bin/example_apps/$alg file $1 filetype edgelist > results/graphchi/$1_$alg 2> err/graphchi/$1_$alg
done
