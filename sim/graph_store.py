from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Dict, List, Tuple, Iterable

import networkx as nx

from .model import World, Transition


class GraphStore:
    """NetworkX DiGraph wrapper for worlds and transitions.

    Worlds are loaded from JSON files in a directory, following the schema described in README.
    """

    def __init__(self) -> None:
        self.G = nx.DiGraph()

    def load_worlds_from_dir(self, worlds_dir: str) -> Dict[str, World]:
        worlds: Dict[str, World] = {}
        if not os.path.isdir(worlds_dir):
            os.makedirs(worlds_dir, exist_ok=True)
        for fname in os.listdir(worlds_dir):
            if not fname.endswith('.json'):
                continue
            path = os.path.join(worlds_dir, fname)
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            world = World(
                world_id=data['world_id'],
                name=data.get('name', data['world_id']),
                description=data.get('description', ''),
                necessary=data.get('necessary', []),
                possible=data.get('possible', []),
                edges=data.get('edges', []),
                arweave_uri=data.get('arweave_uri', 'ar://placeholder'),
                created_by=data.get('created_by', 'sim://anon'),
                created_at=data.get('created_at', ''),
            )
            worlds[world.world_id] = world
        self._build_graph(worlds)
        return worlds

    def _build_graph(self, worlds: Dict[str, World]) -> None:
        self.G.clear()
        for w in worlds.values():
            self.G.add_node(w.world_id, world=w)
        for w in worlds.values():
            for dst in w.edges:
                if dst in worlds:
                    self.G.add_edge(w.world_id, dst)

    def edges(self) -> List[Transition]:
        return [Transition(u, v) for u, v in self.G.edges()]

    def simple_cycles(self) -> List[List[str]]:
        return list(nx.simple_cycles(self.G))

    def descendants(self, world_id: str) -> List[str]:
        return list(nx.descendants(self.G, world_id))

    def save_graph_summary(self, outfile: str) -> None:
        summary = {
            'nodes': list(self.G.nodes()),
            'edges': [(u, v) for u, v in self.G.edges()],
            'cycles': self.simple_cycles(),
        }
        os.makedirs(os.path.dirname(outfile), exist_ok=True)
        with open(outfile, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

    def write_world_jsons(self, worlds: Iterable[World], worlds_dir: str) -> None:
        os.makedirs(worlds_dir, exist_ok=True)
        for w in worlds:
            path = os.path.join(worlds_dir, f"{w.world_id}.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(asdict(w), f, indent=2)


