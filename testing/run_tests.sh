#!/bin/bash
for graph in graphs/{1l,2l,3l,4l,5l,6l,7l}; do
	./run_graph_nets.sh $graph
#	./run_timely.sh $graph
	./run_graphchi.sh $graph
done
