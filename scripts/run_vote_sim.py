#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import random
from typing import Dict

# Ensure project root is on path when running as a script
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

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

    successful_count = 0
    skipped_count = 0
    failed_count = 0

    for prop_id, src, dst in proposals:
        # Read current active world before each proposal (fresh read each time)
        with open(active_path, 'r', encoding='utf-8') as f:
            active_data = json.load(f)
        current_active = active_data.get("active_world", "w1")
        
        # Validate that the proposal's from_world matches the current active world
        if src != current_active:
            print(f"Skipping {prop_id} ({src}→{dst}): Current active world is {current_active}, but proposal requires {src}")
            skipped_count += 1
            continue
        
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
            successful_count += 1
            # Verify active world was updated
            with open(active_path, 'r', encoding='utf-8') as f:
                new_active_data = json.load(f)
            new_active = new_active_data.get("active_world", "w1")
            if new_active != dst:
                print(f"Warning: After {prop_id}, active world is {new_active} but should be {dst}")
        else:
            print(f"Proposal {prop_id} {src}->{dst} failed (quorum={result.quorum_met}, support={result.votes_for}/{result.votes_for+result.votes_against})")
            failed_count += 1
    
    # Print summary
    summary_parts = [f"{successful_count} succeeded"]
    if failed_count > 0:
        summary_parts.append(f"{failed_count} failed")
    if skipped_count > 0:
        summary_parts.append(f"{skipped_count} skipped (wrong active world)")
    summary = ", ".join(summary_parts)
    
    # Read final state
    with open(active_path, 'r', encoding='utf-8') as f:
        final_active_data = json.load(f)
    final_active = final_active_data.get("active_world", "w1")
    
    history_path = os.path.join(examples_dir, "history.json")
    history_count = 0
    if os.path.exists(history_path):
        with open(history_path, 'r', encoding='utf-8') as f:
            history = json.load(f)
            history_count = len(history)
    
    print(f"Simulation complete: {summary} out of {len(proposals)} proposals. History contains {history_count} transitions. Active world: {final_active}")

    print("Simulation complete. See examples/history.json and examples/active_world.json")


if __name__ == "__main__":
    main()


