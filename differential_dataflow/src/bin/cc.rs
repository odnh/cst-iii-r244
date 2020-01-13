extern crate timely;
extern crate graph_map;
extern crate differential_dataflow;

use differential_dataflow::operators::*;
use differential_dataflow::input::InputSession;

use graph_map::GraphMMap;
use std::convert::TryInto;

fn main() {

    let filename = std::env::args().nth(1).unwrap();

    timely::execute_from_args(std::env::args().skip(1), move |worker| {

        let mut input = InputSession::new();

        worker.dataflow(|scope| {
            let edges = input.to_collection(scope);
            let labels = edges.map(|(src,_dest)| (src,src)).distinct();

            labels.iterate(|inner| {
                let edges = edges.enter(&inner.scope());
                let labels = labels.enter(&inner.scope());
                inner.join(&edges)
                     .map(|(_src,(lbl,dst))| (dst,lbl))
                     .concat(&labels)
                     .reduce(|_dst, lbls, out| {
                         let min_lbl =
                             lbls.iter()
                             .map(|x| *x.0)
                             .min()
                             .unwrap();
                         out.push((min_lbl, 1));
                     })
            }).inspect(|x| println!("{:?}", x));
        });

        let graph = GraphMMap::new(&filename);

        input.advance_to(0);
        for node in 1 .. graph.nodes() {
            for &edge in graph.edges(node) {
                input.insert((node, edge.try_into().unwrap()));
            }
        }
    }).unwrap();
}
