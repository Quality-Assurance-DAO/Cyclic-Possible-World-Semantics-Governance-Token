from __future__ import annotations

import json
import os
import random
from typing import Dict, Tuple, List

from .archiver import MockArchiver
from .cardano_sim import CardanoSimulator
from .graph_store import GraphStore
from .model import KripkeModel
from .voting import Voter, Proposal, simulate_votes_random, evaluate_proposal


def ensure_examples_dirs(root: str) -> Tuple[str, str]:
    examples_dir = os.path.join(root, "examples")
    worlds_dir = os.path.join(examples_dir, "worlds")
    os.makedirs(worlds_dir, exist_ok=True)
    return examples_dir, worlds_dir


def load_worlds_and_valuation(examples_dir: str):
    store = GraphStore()
    worlds = store.load_worlds_from_dir(os.path.join(examples_dir, "worlds"))
    valuation_path = os.path.join(examples_dir, "valuation.json")
    valuation = {}
    if os.path.exists(valuation_path):
        with open(valuation_path, 'r', encoding='utf-8') as f:
            valuation = {k: set(v) for k, v in json.load(f).items()}
    model = KripkeModel(worlds, store.edges(), valuation)
    return store, worlds, model


def default_proposals():
    return [
        ("prop-001", "w1", "w2"),
        ("prop-002", "w2", "w3"),
        ("prop-003", "w3", "w4"),
        ("prop-004", "w4", "w1"),
        ("prop-005", "w2", "w1"),
        ("prop-006", "w3", "w2"),
    ]


def build_voters(n: int = 10) -> Dict[str, Voter]:
    return {f"v{i}": Voter(voter_id=f"v{i}", weight=i) for i in range(1, n + 1)}


def run_single_proposal(
    examples_dir: str,
    proposal_id: str,
    from_world: str,
    to_world: str,
    quorum: float,
    threshold: float,
    rng: random.Random,
    approval_probability: float,
    participation_probability: float,
    voters: Dict[str, Voter],
):
    proposal = Proposal(proposal_id=proposal_id, from_world=from_world, to_world=to_world, quorum=quorum, threshold=threshold)
    votes = simulate_votes_random(voters, rng, approval_probability=approval_probability, participation_probability=participation_probability)
    result = evaluate_proposal(proposal, voters, votes)
    if not result.passed:
        return None, result
    archiver = MockArchiver()
    chain = CardanoSimulator(examples_dir)
    src_data = json.load(open(os.path.join(examples_dir, "worlds", f"{from_world}.json"), 'r', encoding='utf-8'))
    dst_data = json.load(open(os.path.join(examples_dir, "worlds", f"{to_world}.json"), 'r', encoding='utf-8'))
    ar_src = archiver.upload_json(src_data)
    ar_dst = archiver.upload_json(dst_data)
    tx = chain.submit_transition(
        proposal_id=proposal_id,
        from_world=from_world,
        to_world=to_world,
        arweave_from=ar_src,
        arweave_to=ar_dst,
        votes_for=result.votes_for,
        votes_against=result.votes_against,
        quorum=quorum,
        signers=["gov_key1", "gov_key2"],
    )
    return tx, result


