from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from graph_nets import blocks
from graph_nets import graphs
from graph_nets import modules
from graph_nets import utils_np
from graph_nets import utils_tf

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import sonnet as snt
import tensorflow as tf

import sys
import time

"""# Helper functions"""

def plot_graph_networkx(graph, ax, pos=None):
  node_labels = {node: "{:.3g}".format(data["features"][0])
                 for node, data in graph.nodes(data=True)
                 if data["features"] is not None}
  edge_labels = {(sender, receiver): "{:.3g}".format(data["features"][0])
                 for sender, receiver, data in graph.edges(data=True)
                 if data["features"] is not None}
  global_label = ("{:.3g}".format(graph.graph["features"][0])
                  if graph.graph["features"] is not None else None)

  if pos is None:
    pos = nx.spring_layout(graph)
  nx.draw_networkx(graph, pos, ax=ax, labels=node_labels)

  if edge_labels:
    nx.draw_networkx_edge_labels(graph, pos, edge_labels, ax=ax)

  if global_label:
    plt.text(0.05, 0.95, global_label, transform=ax.transAxes)

  ax.yaxis.set_visible(False)
  ax.xaxis.set_visible(False)
  return pos

def plot_compare_graphs(graphs_tuples, labels):
  pos = None
  num_graphs = len(graphs_tuples)
  _, axes = plt.subplots(1, num_graphs, figsize=(5*num_graphs, 5))
  if num_graphs == 1:
    axes = axes,
  pos = None
  for name, graphs_tuple, ax in zip(labels, graphs_tuples, axes):
    graph = utils_np.graphs_tuple_to_networkxs(graphs_tuple)[0]
    pos = plot_graph_networkx(graph, ax, pos=pos)
    ax.set_title(name)


"""# SSSP"""

class SSSPEdge(snt.AbstractModule):
  def __init__(self, output_size=10, name="ssspedge"):
    super(SSSPEdge, self).__init__(name=name)
    self._output_size = output_size

  def _build(self, inputs):
    return tf.stack([inputs[:,0], tf.add(inputs[:,0], inputs[:,2])], 1)

class SSSPNode(snt.AbstractModule):
  def __init__(self, output_size=10, name="ssspnode"):
    super(SSSPNode, self).__init__(name=name)
    self._output_size = output_size

  def _build(self, inputs):
    minimums = tf.math.minimum(inputs[:,1], inputs[:,2])
    changed = tf.dtypes.cast(tf.math.equal(minimums, inputs[:,2]), dtype=tf.float32)
    return tf.stack([minimums, changed], 1)

tf.reset_default_graph()
sssp_edge_block = lambda: blocks.EdgeBlock(
    edge_model_fn=lambda: SSSPEdge(output_size=10),
    use_edges=True,
    use_receiver_nodes=False,
    use_sender_nodes=True,
    use_globals=False,
    name="edge_block")

sssp_node_block = lambda:  blocks.NodeBlock(
    node_model_fn=lambda: SSSPNode(output_size=10),
    use_received_edges=True,
    use_sent_edges=False,
    use_nodes=True,
    use_globals=False,
    received_edges_reducer=tf.math.unsorted_segment_min,
    sent_edges_reducer=tf.math.unsorted_segment_sum,
    name="node_block")


"""# PageRank"""

class PREdge(snt.AbstractModule):
  def __init__(self, output_size=10, name="predge"):
    super(PREdge, self).__init__(name=name)
    self._output_size = output_size

  def _build(self, inputs):
    return tf.math.divide(tf.slice(inputs, [0,1], [inputs.get_shape()[0],1]),
                          tf.slice(inputs, [0,2], [inputs.get_shape()[0],1]))

class PRNode(snt.AbstractModule):
  def __init__(self, add_factor, d, output_size=10, name="prnode"):
    super(PRNode, self).__init__(name=name)
    self._output_size = output_size
    self.add_factor = add_factor
    self.d = d

  def _build(self, inputs):
    const_to_add = tf.math.scalar_mul(self.add_factor, tf.ones(inputs.get_shape()[0], dtype=tf.dtypes.float32))
    new_probs = tf.math.add(const_to_add, tf.math.scalar_mul(self.d, inputs[:,0]))
    return tf.stack([new_probs, inputs[:,2]], 1)

tf.reset_default_graph()
pr_edge_block = lambda: blocks.EdgeBlock(
    edge_model_fn=lambda: PREdge(output_size=10),
    use_edges=True,
    use_receiver_nodes=False,
    use_sender_nodes=True,
    use_globals=False,
    name="edge_block")

pr_node_block = lambda add_factor, d: blocks.NodeBlock(
    node_model_fn=lambda: PRNode(add_factor, d, output_size=10),
    use_received_edges=True,
    use_sent_edges=False,
    use_nodes=True,
    use_globals=False,
    received_edges_reducer=tf.math.unsorted_segment_sum,
    sent_edges_reducer=tf.math.unsorted_segment_sum,
    name="node_block")


"""# Connected Components"""

class CCEdge(snt.AbstractModule):
  def __init__(self, output_size=10, name="ccedge"):
    super(CCEdge, self).__init__(name=name)
    self._output_size = output_size

  def _build(self, inputs):
    return tf.stack([inputs[:,0], inputs[:,2]], 1)

class CCNode(snt.AbstractModule):
  def __init__(self, output_size=10, name="ccnode"):
    super(CCNode, self).__init__(name=name)
    self._output_size = output_size

  def _build(self, inputs):
    minimums = tf.math.minimum(inputs[:,1], inputs[:,2])
    changed = tf.dtypes.cast(tf.math.equal(minimums, inputs[:,2]), dtype=tf.float32)
    return tf.stack([minimums, changed], 1)

tf.reset_default_graph()
cc_edge_block = lambda: blocks.EdgeBlock(
    edge_model_fn=lambda: CCEdge(output_size=10),
    use_edges=True,
    use_receiver_nodes=False,
    use_sender_nodes=True,
    use_globals=False,
    name="edge_block")

cc_node_block = lambda: blocks.NodeBlock(
    node_model_fn=lambda: CCNode(output_size=10),
    use_received_edges=True,
    use_sent_edges=False,
    use_nodes=True,
    use_globals=False,
    received_edges_reducer=tf.math.unsorted_segment_min,
    sent_edges_reducer=tf.math.unsorted_segment_sum,
    name="node_block")


"""# Functions to preprocess input graphs"""

def read_graph(filename):
  fp = open(filename, 'r')
  senders = []
  receivers = []
  for line in fp:
    pairs = list(map(lambda x: int(x)-1, line.split()))
    senders.append(pairs[0])
    receivers.append(pairs[1])
  num_nodes = max(max(senders), max(receivers)) + 1
  return (senders, receivers, num_nodes)

def make_sssp_graph(graph):
  return {
      "globals": np.zeros(1).astype(np.float32),
      "nodes": np.repeat([[0., 0.], [np.inf, 0.]], [1, graph[2]], axis=0).astype(np.float32),
      "edges": np.c_[np.ones(len(graph[0])).astype(np.float32), np.zeros(len(graph[0])).astype(np.float32)],
      "senders": graph[0],
      "receivers": graph[1],
  }

def make_cc_graph(graph):
  senders = graph[0]
  receivers = graph[1]
  return {
      "globals": np.zeros(1).astype(np.float32),
      "nodes": np.c_[np.arange(graph[2]).astype(np.float32), np.zeros(graph[2]).astype(np.float32)],
      "edges": np.c_[ np.zeros(len(graph[0])*2).astype(np.float32), np.zeros(len(graph[0])*2).astype(np.float32)],
      "senders": np.hstack([senders, receivers]),
      "receivers": np.hstack([receivers, senders])
  }

def make_pr_graph(graph):
  node_probs = np.full((graph[2], 1), 1.0/graph[2]).astype(np.float32)
  node_links = np.bincount(graph[0], minlength=graph[2]).astype(np.float32)
  return {
      "globals": np.zeros(1).astype(np.float32),
      "nodes": np.c_[node_probs, node_links],
      "edges": np.zeros((len(graph[0]), 1)).astype(np.float32),
      "senders": graph[0],
      "receivers": graph[1]
  }

"""# Functions to run algorithms"""

def run_sssp(filename):
  tf.reset_default_graph()
  input_graphs = utils_tf.data_dicts_to_graphs_tuple([make_sssp_graph(read_graph(filename))])

  node_block = sssp_node_block()
  edge_block = sssp_edge_block()
  sssp_step = lambda graph: node_block(edge_block(graph))

  g0 = input_graphs
  i0 = tf.constant(0)
  c = lambda g, i: tf.equal(tf.math.reduce_min(g.nodes[:,1]), 0)
  b = lambda g, i: (sssp_step(g), i+1)
  r = tf.while_loop(c, b, [g0, i0], return_same_structure=True)

  sess = tf.compat.v1.Session()
  (result_g, steps) = sess.run(r)
  sess.close()

  return (result_g, steps)

def run_cc(filename):
  tf.reset_default_graph()
  input_graphs = utils_tf.data_dicts_to_graphs_tuple([make_cc_graph(read_graph(filename))])

  node_block = cc_node_block()
  edge_block = cc_edge_block()
  cc_step = lambda graph: node_block(edge_block(graph))

  g0 = input_graphs
  i0 = tf.constant(0)
  c = lambda g, i: tf.equal(tf.math.reduce_min(g.nodes[:,1]), 0)
  b = lambda g, i: (cc_step(g), i+1)
  r = tf.while_loop(c, b, [g0, i0], return_same_structure=True)

  sess = tf.compat.v1.Session()
  (result_g, steps) = sess.run(r)
  sess.close()

  return (result_g, steps)

def run_pr(filename, iterations):
  tf.reset_default_graph()
  raw_graph = read_graph(filename)
  input_graphs = utils_tf.data_dicts_to_graphs_tuple([make_pr_graph(raw_graph)])

  add_factor = tf.constant((1-0.5)/raw_graph[2])
  d = tf.constant(0.5)
  tfiters = tf.constant(iterations)

  node_block = pr_node_block(add_factor, d)
  edge_block = pr_edge_block()
  pr_step = lambda graph: node_block(edge_block(graph))

  g0 = input_graphs
  i0 = tf.constant(0)
  c = lambda g, i: i < tfiters
  b = lambda g, i: (pr_step(g), i+1)
  r = tf.while_loop(c, b, [g0, i0], return_same_structure=True)

  sess = tf.compat.v1.Session()
  (result_g, steps) = sess.run(r)
  sess.close()

  return (result_g, steps)

"""# Handle cli usage"""

alg = int(sys.argv[1])
fname = sys.argv[2]

start_time = time.time()
res = [run_cc, run_sssp, lambda f: run_pr(f, 10)][alg](fname)
end_time = time.time()
np.set_printoptions(threshold=sys.maxsize)
print(res[0].nodes)
print("Steps:", res[1])
print("TriIme:", end_time - start_time)
