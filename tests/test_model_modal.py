from __future__ import annotations

from sim.model import World, Transition, KripkeModel


def build_example_model():
    worlds = {
        "w1": World("w1", "w1", "", [], [], ["w2"]),
        "w2": World("w2", "w2", "", [], [], ["w3", "w1"]),
        "w3": World("w3", "w3", "", [], [], ["w4", "w2"]),
        "w4": World("w4", "w4", "", [], [], ["w1"]),
    }
    edges = [
        Transition("w1", "w2"),
        Transition("w2", "w3"),
        Transition("w3", "w4"),
        Transition("w4", "w1"),
        Transition("w2", "w1"),
        Transition("w3", "w2"),
    ]
    valuation = {
        "p1": {"w1", "w2", "w3"},
        "p2": {"w2", "w3", "w4"},
        "p3": {"w3", "w4"},
        "p4": {"w4"},
    }
    return KripkeModel(worlds, edges, valuation)


def test_modal_necessity_and_possibility():
    m = build_example_model()
    # □p1 at w1? successors(w1)={w2}; p1 true at w2 => True
    assert m.is_necessary("p1", "w1") is True
    # □p1 at w3? successors={w4,w2}; p1 false at w4 => False
    assert m.is_necessary("p1", "w3") is False
    # ◇p4 at w3? successors include w4 where p4 true => True
    assert m.is_possible("p4", "w3") is True
    # ◇p4 at w1? successor w2 does not have p4 => False
    assert m.is_possible("p4", "w1") is False


