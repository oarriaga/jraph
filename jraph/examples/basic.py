# Copyright 2020 DeepMind Technologies Limited.


# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
r"""A basic graphnet example.

This example just explains the bare mechanics of the library.
"""

import logging

from absl import app
import jax
import jax.numpy as jnp
import jraph
import numpy as np

MASK_BROKEN_MSG = ("Support for jax.mask is currently broken. This is not a "
                   "jraph error.")


def run():
  """Runs basic example."""

  # Creating graph tuples.

  # Creates a GraphsTuple from scratch containing a single graph.
  # The graph has 3 nodes and 2 edges.
  # Each node has a 4-dimensional feature vector.
  # Each edge has a 5-dimensional feature vector.
  # The graph itself has a 6-dimensional feature vector.
  single_graph = jraph.GraphsTuple(
      n_node=np.asarray([3]), n_edge=np.asarray([2]),
      nodes=np.ones((3, 4)), edges=np.ones((2, 5)),
      globals=np.ones((1, 6)),
      senders=np.array([0, 1]), receivers=np.array([2, 2]))
  logging.info("Single graph %r", single_graph)

  # Creates a GraphsTuple from scratch containing a single graph with nested
  # feature vectors.
  # The graph has 3 nodes and 2 edges.
  # The feature vector can be arbitrary nested types of dict, list and tuple,
  # or any other type you registered with jax.tree_util.register_pytree_node.
  nested_graph = jraph.GraphsTuple(
      n_node=np.asarray([3]), n_edge=np.asarray([2]),
      nodes={"a": np.ones((3, 4))}, edges={"b": np.ones((2, 5))},
      globals={"c": np.ones((1, 6))},
      senders=np.array([0, 1]), receivers=np.array([2, 2]))
  logging.info("Nested graph %r", nested_graph)

  # Creates a GraphsTuple from scratch containing a 2 graphs using an implicit
  # batch dimension.
  # The first graph has 3 nodes and 2 edges.
  # The second graph has 1 nodes and 1 edges.
  # Each node has a 4-dimensional feature vector.
  # Each edge has a 5-dimensional feature vector.
  # The graph itself has a 6-dimensional feature vector.
  implicitly_batched_graph = jraph.GraphsTuple(
      n_node=np.asarray([3, 1]), n_edge=np.asarray([2, 1]),
      nodes=np.ones((4, 4)), edges=np.ones((3, 5)),
      globals=np.ones((2, 6)),
      senders=np.array([0, 1, 3]), receivers=np.array([2, 2, 3]))
  logging.info("Implicitly batched graph %r", implicitly_batched_graph)

  # Creates a GraphsTuple from two existing GraphsTuple using an implicit
  # batch dimension.
  # The GraphsTuple will contain three graphs.
  implicitly_batched_graph = jraph.batch(
      [single_graph, implicitly_batched_graph])
  logging.info("Implicitly batched graph %r", implicitly_batched_graph)

  # Creates multiple GraphsTuples from an existing GraphsTuple with an implicit
  # batch dimension.
  graph_1, graph_2, graph_3 = jraph.unbatch(implicitly_batched_graph)
  logging.info("Unbatched graphs %r %r %r", graph_1, graph_2, graph_3)

  # Creates a padded GraphsTuple from an existing GraphsTuple.
  # The padded GraphsTuple will contain 10 nodes, 5 edges, and 4 graphs.
  # Three graphs are added for the padding.
  # First an dummy graph which contains the padding nodes and edges and secondly
  # two empty graphs without nodes or edges to pad out the graphs.
  padded_graph = jraph.pad_with_graphs(
      single_graph, n_node=10, n_edge=5, n_graph=4)
  logging.info("Padded graph %r", padded_graph)

  # Creates a GraphsTuple from an existing padded GraphsTuple.
  # The previously added padding is removed.
  single_graph = jraph.unpad_with_graphs(padded_graph)
  logging.info("Unpadded graph %r", single_graph)

  # Creates a GraphsTuple containing a 2 graphs using an explicit batch
  # dimension.
  # An explicit batch dimension requires more memory, but can simplify
  # the definition of functions operating on the graph.
  # Explicitly batched graphs require the GraphNetwork to be transformed
  # by jax.mask followed by jax.vmap.
  # Using an explicit batch requires padding all feature vectors to
  # the maximum size of nodes and edges.
  # The first graph has 3 nodes and 2 edges.
  # The second graph has 1 nodes and 1 edges.
  # Each node has a 4-dimensional feature vector.
  # Each edge has a 5-dimensional feature vector.
  # The graph itself has a 6-dimensional feature vector.
  explicitly_batched_graph = jraph.GraphsTuple(
      n_node=np.asarray([[3], [1]]), n_edge=np.asarray([[2], [1]]),
      nodes=np.ones((2, 3, 4)), edges=np.ones((2, 2, 5)),
      globals=np.ones((2, 1, 6)),
      senders=np.array([[0, 1], [0, -1]]),
      receivers=np.array([[2, 2], [0, -1]]))
  logging.info("Explicitly batched graph %r", explicitly_batched_graph)

  # Running a graph propagation steps.
  # First define the update functions for the edges, nodes and globals.
  # In this example we use the identity everywhere.
  # For Graph neural networks, each update function is typically a neural
  # network.
  def update_edge_fn(
      edge_features,
      sender_node_features,
      receiver_node_features,
      globals_):
    """Returns the update edge features."""
    del sender_node_features
    del receiver_node_features
    del globals_
    return edge_features

  def update_node_fn(
      node_features,
      aggregated_sender_edge_features,
      aggregated_receiver_edge_features,
      globals_):
    """Returns the update node features."""
    del aggregated_sender_edge_features
    del aggregated_receiver_edge_features
    del globals_
    return node_features

  def update_globals_fn(
      aggregated_node_features,
      aggregated_edge_features,
      globals_):
    del aggregated_node_features
    del aggregated_edge_features
    return globals_

  # Optionally define custom aggregation functions.
  # In this example we use the defaults (so no need to define them explicitly).
  aggregate_edges_for_nodes_fn = jax.ops.segment_sum
  aggregate_nodes_for_globals_fn = jax.ops.segment_sum
  aggregate_edges_for_globals_fn = jax.ops.segment_sum

  # Optionally define attention logit function and attention reduce function.
  # This can be used for graph attention.
  # The attention function calculates attention weights, and the apply
  # attention function calculates the new edge feature given the weights.
  # We don't use graph attention here, and just pass the defaults.
  attention_logit_fn = None
  attention_reduce_fn = None

  # Creates a new GraphNetwork in its most general form.
  # Most of the arguments have defaults and can be omitted if a feature
  # is not used.
  # There are also predefined GraphNetworks available (see models.py)
  network = jraph.GraphNetwork(
      update_edge_fn=update_edge_fn,
      update_node_fn=update_node_fn,
      update_global_fn=update_globals_fn,
      attention_logit_fn=attention_logit_fn,
      aggregate_edges_for_nodes_fn=aggregate_edges_for_nodes_fn,
      aggregate_nodes_for_globals_fn=aggregate_nodes_for_globals_fn,
      aggregate_edges_for_globals_fn=aggregate_edges_for_globals_fn,
      attention_reduce_fn=attention_reduce_fn)

  # Runs graph propagation on (implicitly batched) graphs.
  updated_graph = network(single_graph)
  logging.info("Updated graph from single graph %r", updated_graph)

  updated_graph = network(nested_graph)
  logging.info("Updated graph from nested graph %r", nested_graph)

  updated_graph = network(implicitly_batched_graph)
  logging.info("Updated graph from implicitly batched graph %r", updated_graph)

  updated_graph = network(padded_graph)
  logging.info("Updated graph from padded graph %r", updated_graph)

  # Runs graph propagation on an explicitly batched graph.
  # WARNING: This code relies on an undocumented JAX feature (jax.mask) which
  # might stop working at any time!
  graph_shape = jraph.GraphsTuple(
      n_node="(g)",
      n_edge="(g)",
      nodes="(n, {})".format(explicitly_batched_graph.nodes.shape[-1]),
      edges="(e, {})".format(explicitly_batched_graph.edges.shape[-1]),
      globals="(g, {})".format(explicitly_batched_graph.globals.shape[-1]),
      senders="(e)",
      receivers="(e)")
  batch_size = explicitly_batched_graph.globals.shape[0]
  logical_env = {"g": jnp.ones(batch_size, dtype=jnp.int32),
                 "n": jnp.sum(explicitly_batched_graph.n_node, axis=-1),
                 "e": jnp.sum(explicitly_batched_graph.n_edge, axis=-1)}
  try:
    propagation_fn = jax.vmap(jax.mask(
        network, in_shapes=[graph_shape], out_shape=graph_shape))
    updated_graph = propagation_fn([explicitly_batched_graph], logical_env)
    logging.info("Updated graph from explicitly batched graph %r",
                 updated_graph)
  except Exception:  # pylint: disable=broad-except
    logging.warning(MASK_BROKEN_MSG)

  # JIT-compile graph propagation.
  # Use padded graphs to avoid re-compilation at every step!
  jitted_network = jax.jit(network)
  updated_graph = jitted_network(padded_graph)
  logging.info("(JIT) updated graph from padded graph %r", updated_graph)

  # Or use an explicit batch dimension.
  try:
    jitted_propagation_fn = jax.jit(propagation_fn)
    updated_graph = jitted_propagation_fn(
        [explicitly_batched_graph], logical_env)
    logging.info("(JIT) Updated graph from explicitly batched graph %r",
                 updated_graph)
  except Exception:  # pylint: disable=broad-except
    logging.warning(MASK_BROKEN_MSG)

  logging.info("basic.py complete!")


def main(argv):
  if len(argv) > 1:
    raise app.UsageError("Too many command-line arguments.")
  run()


if __name__ == "__main__":
  app.run(main)
