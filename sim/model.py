from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set, List, Iterable


@dataclass(frozen=True)
class World:
    """Immutable description of a world with basic metadata.

    The truth assignment for propositions is not stored here; it belongs to the KripkeModel valuation.
    """

    world_id: str
    name: str
    description: str
    necessary: List[str] = field(default_factory=list)
    possible: List[str] = field(default_factory=list)
    edges: List[str] = field(default_factory=list)
    arweave_uri: str = "ar://placeholder"
    created_by: str = "sim://anon"
    created_at: str = ""


@dataclass(frozen=True)
class Transition:
    """Directed transition between worlds."""

    from_world: str
    to_world: str


class KripkeModel:
    """Kripke model with a directed frame and a valuation.

    - Frame: set of worlds W and accessibility relation R ⊆ W×W
    - Valuation: mapping V: Prop -> set of worlds where the proposition holds
    """

    def __init__(self, worlds: Dict[str, World], edges: Iterable[Transition], valuation: Dict[str, Set[str]]):
        self.worlds: Dict[str, World] = dict(worlds)
        self.relations: Dict[str, Set[str]] = {w: set() for w in worlds}
        for t in edges:
            if t.from_world not in self.worlds or t.to_world not in self.worlds:
                raise ValueError(f"Unknown world in transition {t}")
            self.relations[t.from_world].add(t.to_world)
        # valuation maps proposition -> set of world_ids where true
        self.valuation: Dict[str, Set[str]] = {p: set(ws) for p, ws in valuation.items()}

    def successors(self, world_id: str) -> Set[str]:
        return set(self.relations.get(world_id, set()))

    def is_true(self, prop: str, world_id: str) -> bool:
        return world_id in self.valuation.get(prop, set())

    def is_necessary(self, prop: str, world_id: str) -> bool:
        """□p true in w iff p true in all R-successors of w.
        Convention: if w has no successors, □p is vacuously true.
        """
        succ = self.successors(world_id)
        if not succ:
            return True
        return all(self.is_true(prop, w) for w in succ)

    def is_possible(self, prop: str, world_id: str) -> bool:
        """◇p true in w iff p true in some R-successor of w.
        Convention: if w has no successors, ◇p is false.
        """
        succ = self.successors(world_id)
        if not succ:
            return False
        return any(self.is_true(prop, w) for w in succ)

    def summarize_world_label(self, world_id: str, props: List[str]) -> str:
        true_props = [p for p in props if self.is_true(p, world_id)]
        return f"{world_id}:" + ("{" + ",".join(true_props) + "}" if true_props else "{}")


