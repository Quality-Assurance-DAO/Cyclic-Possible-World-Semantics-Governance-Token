from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class TransitionTx:
    tx_id: str
    proposal_id: str
    from_world: str
    to_world: str
    arweave_from: str
    arweave_to: str
    votes_for: int
    votes_against: int
    quorum: float
    timestamp: str
    signers: List[str]
    notes: str = "simulation run"


class CardanoSimulator:
    """Simulated Cardano transaction builder and active world registry manager."""

    def __init__(self, examples_dir: str, persistence=None) -> None:
        self.examples_dir = examples_dir
        os.makedirs(self.examples_dir, exist_ok=True)
        self.history_path = os.path.join(self.examples_dir, "history.json")
        self.active_path = os.path.join(self.examples_dir, "active_world.json")
        self.persistence = persistence

    def _read_history(self) -> List[Dict[str, Any]]:
        if self.persistence is not None:
            data = self.persistence.read_json("history.json")
            return data or []
        if not os.path.exists(self.history_path):
            return []
        with open(self.history_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _write_history(self, history: List[Dict[str, Any]]) -> None:
        if self.persistence is not None:
            self.persistence.write_json("history.json", history)  # type: ignore
            return
        with open(self.history_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)

    def _write_active(self, world_id: str, tx_id: str) -> None:
        active = {
            "active_world": world_id,
            "last_tx": tx_id,
            "updated_at": now_iso(),
        }
        if self.persistence is not None:
            self.persistence.write_json("active_world.json", active)
            return
        with open(self.active_path, 'w', encoding='utf-8') as f:
            json.dump(active, f, indent=2)

    def submit_transition(
        self,
        proposal_id: str,
        from_world: str,
        to_world: str,
        arweave_from: str,
        arweave_to: str,
        votes_for: int,
        votes_against: int,
        quorum: float,
        signers: List[str],
        notes: str = "simulation run",
    ) -> TransitionTx:
        tx = TransitionTx(
            tx_id=str(uuid.uuid4()),
            proposal_id=proposal_id,
            from_world=from_world,
            to_world=to_world,
            arweave_from=arweave_from,
            arweave_to=arweave_to,
            votes_for=votes_for,
            votes_against=votes_against,
            quorum=quorum,
            timestamp=now_iso(),
            signers=signers,
            notes=notes,
        )
        history = self._read_history()
        history.append(asdict(tx))
        self._write_history(history)
        self._write_active(to_world, tx.tx_id)
        return tx


# Real pycardano/Blockfrost integration hint (commented):
# from pycardano import *
# class CardanoAdapter:
#     def __init__(self, blockfrost_key: str, network: Network):
#         # setup network, wallet, etc.
#         ...
#     def submit_transition(self, ...):
#         # build tx with metadata, sign and submit, return tx hash
#         ...


