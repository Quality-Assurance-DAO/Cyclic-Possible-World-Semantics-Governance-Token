#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

# Ensure project root is on path when running as a script
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sim.graph_store import GraphStore
from sim.model import World
from sim.tokenize import write_metadata_json


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> None:
    root = os.path.dirname(os.path.dirname(__file__))
    examples_dir = os.path.join(root, "examples")
    worlds_dir = os.path.join(examples_dir, "worlds")
    os.makedirs(worlds_dir, exist_ok=True)

    # Define example worlds w1..w4
    worlds = [
        World(
            world_id="w1",
            name="Base Governance",
            description="Baseline; minimal rules",
            necessary=["p1"],
            possible=["transition_to_w2"],
            edges=["w2"],
            arweave_uri="ar://placeholder",
            created_by="sim://user1",
            created_at=now_iso(),
        ),
        World(
            world_id="w2",
            name="Quorum Enabled",
            description="Quorum 50% enabled",
            necessary=["p1", "p2"],
            possible=["transition_to_w3", "revert_to_w1"],
            edges=["w3", "w1"],
            arweave_uri="ar://placeholder",
            created_by="sim://user1",
            created_at=now_iso(),
        ),
        World(
            world_id="w3",
            name="Delegated Governance",
            description="Delegation enabled; quorum 50%",
            necessary=["p1", "p2", "p3"],
            possible=["transition_to_w4", "revert_to_w2"],
            edges=["w4", "w2"],
            arweave_uri="ar://placeholder",
            created_by="sim://user1",
            created_at=now_iso(),
        ),
        World(
            world_id="w4",
            name="Council Governance",
            description="Council created; strong rules",
            necessary=["p2", "p3", "p4"],
            possible=["reset_w1"],
            edges=["w1"],
            arweave_uri="ar://placeholder",
            created_by="sim://user1",
            created_at=now_iso(),
        ),
    ]

    # Write world JSONs and metadata
    store = GraphStore()
    store.write_world_jsons(worlds, worlds_dir)

    for w in worlds:
        write_metadata_json(w, os.path.join(worlds_dir, f"{w.world_id}.metadata.json"))

    # Build graph from world files and save summary
    store.load_worlds_from_dir(worlds_dir)
    store.save_graph_summary(os.path.join(examples_dir, "graph.json"))

    # Also write valuation truth table for p1..p4 as example
    valuation = {
        "p1": ["w1", "w2", "w3"],
        "p2": ["w2", "w3", "w4"],
        "p3": ["w3", "w4"],
        "p4": ["w4"],
    }
    with open(os.path.join(examples_dir, "valuation.json"), 'w', encoding='utf-8') as f:
        json.dump(valuation, f, indent=2)

    print("Initialized example worlds and graph summary in examples/.")


if __name__ == "__main__":
    main()


