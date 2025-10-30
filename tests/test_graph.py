from __future__ import annotations

from sim.graph_store import GraphStore
from sim.model import World


def test_cycles_and_reachability(tmp_path):
    worlds = [
        World("w1", "w1", "", edges=["w2"]),
        World("w2", "w2", "", edges=["w3", "w1"]),
        World("w3", "w3", "", edges=["w4", "w2"]),
        World("w4", "w4", "", edges=["w1"]),
    ]
    store = GraphStore()
    wdir = tmp_path / "worlds"
    store.write_world_jsons(worlds, str(wdir))
    store.load_worlds_from_dir(str(wdir))
    cycles = store.simple_cycles()
    assert any(set(cycle) == {"w1", "w2", "w3", "w4"} for cycle in cycles)
    assert set(store.descendants("w2")) >= {"w1", "w3", "w4"}


