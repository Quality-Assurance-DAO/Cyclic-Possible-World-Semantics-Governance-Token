#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys

import networkx as nx

# Ensure project root is on path when running as a script
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sim.graph_store import GraphStore
from sim.model import KripkeModel, Transition
from sim.visualize import draw_graph_png, draw_timeline


def main() -> None:
    root = os.path.dirname(os.path.dirname(__file__))
    examples_dir = os.path.join(root, "examples")
    worlds_dir = os.path.join(examples_dir, "worlds")

    store = GraphStore()
    worlds = store.load_worlds_from_dir(worlds_dir)

    # Labels: world_id plus short prop summary from valuation
    valuation_path = os.path.join(examples_dir, "valuation.json")
    if os.path.exists(valuation_path):
        with open(valuation_path, 'r', encoding='utf-8') as f:
            valuation = {k: set(v) for k, v in json.load(f).items()}
    else:
        valuation = {}

    model = KripkeModel(worlds, store.edges(), valuation)
    props = sorted(list(valuation.keys()))
    labels = {w: model.summarize_world_label(w, props) for w in worlds}

    # Active world
    active_path = os.path.join(examples_dir, "active_world.json")
    active_world = "w1"
    if os.path.exists(active_path):
        with open(active_path, 'r', encoding='utf-8') as f:
            active_world = json.load(f).get("active_world", "w1")

    # Draw graph
    out_graph = os.path.join(examples_dir, "graph.png")
    draw_graph_png(store.G, active_world, labels, out_graph)

    # Draw timeline
    out_timeline = os.path.join(examples_dir, "timeline.png")
    draw_timeline(os.path.join(examples_dir, "history.json"), out_timeline)

    print("Wrote:", out_graph, out_timeline)


if __name__ == "__main__":
    main()


