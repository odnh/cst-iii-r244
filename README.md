# Using Graph Nets for graph algorithm execution

This code is from my final project for the Cambridge Computer Science Part III course R244: Large Scale Data Processing and Optimisation.
Graph Nets is a system to use graph neural networks on top of TensorFlow. This project instead uses it for generic graph algorithm execution and compares the results to those of GraphChi (and differential dataflow)

## Diretory layout:
- `graph_nets`: python script to execute SSSP, CC and PR given a graph in edgelist format
- `graphchi`: implementation of SSSP for GraphChi (CC and PR can be found as examples in the official project repository on GitHub)
- `testing`: contains the scripts used to generate the three graph types and run the tests for the different systems and algorithms over said graph types
- `report`: contains tex files to build the pdf report/write-up of the study
