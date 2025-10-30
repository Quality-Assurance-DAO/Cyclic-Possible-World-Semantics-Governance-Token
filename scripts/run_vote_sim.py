#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import random
from typing import Dict

from sim.archiver import MockArchiver
from sim.cardano_sim import CardanoSimulator
from sim.graph_store import GraphStore
from sim.model import KripkeModel, Transition
from sim.voting import Voter, Proposal, simulate_votes_random, evaluate_proposal


def load_worlds_and_valuation(examples_dir: str):
    store = GraphStore()
    worlds = store.load_worlds_from_dir(os.path.join(examples_dir, "worlds"))
    with open(os.path.join(examples_dir, "valuation.json"), 'r', encoding='utf-8') as f:
        valuation = {k: set(v) for k, v in json.load(f).items()}
    model = KripkeModel(worlds, store.edges(), valuation)
    return store, worlds, model


def default_proposals():
    # Six proposals including reversals
    return [
        ("prop-001", "w1", "w2"),
        ("prop-002", "w2", "w3"),
        ("prop-003", "w3", "w4"),
        ("prop-004", "w4", "w1"),  # reset
        ("prop-005", "w2", "w1"),  # reverse edge
        ("prop-006", "w3", "w2"),  # reverse edge
    ]


def build_voters(n: int = 10) -> Dict[str, Voter]:
    voters: Dict[str, Voter] = {}
    for i in range(1, n + 1):
        voters[f"v{i}"] = Voter(voter_id=f"v{i}", weight=i)  # weights 1..n
    return voters


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--quorum", type=float, default=0.5)
    parser.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    root = os.path.dirname(os.path.dirname(__file__))
    examples_dir = os.path.join(root, "examples")
    store, worlds, model = load_worlds_and_valuation(examples_dir)

    # Initial active world defaults to w1 if not present
    active_path = os.path.join(examples_dir, "active_world.json")
    if not os.path.exists(active_path):
        with open(active_path, 'w', encoding='utf-8') as f:
            json.dump({"active_world": "w1", "last_tx": None, "updated_at": None}, f, indent=2)

    voters = build_voters(10)
    proposals = default_proposals()
    archiver = MockArchiver()
    chain = CardanoSimulator(examples_dir)

    for prop_id, src, dst in proposals:
        proposal = Proposal(proposal_id=prop_id, from_world=src, to_world=dst, quorum=args.quorum, threshold=args.threshold)
        votes = simulate_votes_random(voters, rng, approval_probability=0.6, participation_probability=0.95)
        result = evaluate_proposal(proposal, voters, votes)
        if result.passed:
            # Simulate uploading both worlds' JSON as Arweave payloads
            src_data = json.load(open(os.path.join(examples_dir, "worlds", f"{src}.json"), 'r', encoding='utf-8'))
            dst_data = json.load(open(os.path.join(examples_dir, "worlds", f"{dst}.json"), 'r', encoding='utf-8'))
            ar_src = archiver.upload_json(src_data)
            ar_dst = archiver.upload_json(dst_data)
            tx = chain.submit_transition(
                proposal_id=prop_id,
                from_world=src,
                to_world=dst,
                arweave_from=ar_src,
                arweave_to=ar_dst,
                votes_for=result.votes_for,
                votes_against=result.votes_against,
                quorum=proposal.quorum,
                signers=["gov_key1", "gov_key2"],
            )
            print(f"TX {tx.tx_id}: {src} -> {dst} (passed)")
        else:
            print(f"Proposal {prop_id} {src}->{dst} failed (quorum={result.quorum_met}, support={result.votes_for}/{result.votes_for+result.votes_against})")

    print("Simulation complete. See examples/history.json and examples/active_world.json")


if __name__ == "__main__":
    main()


