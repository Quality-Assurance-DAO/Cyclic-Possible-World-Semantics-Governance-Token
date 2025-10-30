from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional


@dataclass(frozen=True)
class Voter:
    voter_id: str
    weight: int = 1


@dataclass
class Proposal:
    proposal_id: str
    from_world: str
    to_world: str
    quorum: float = 0.5
    threshold: float = 0.5  # majority or supermajority on participating weights


@dataclass
class VoteResult:
    votes_for: int
    votes_against: int
    total_possible_weight: int
    quorum_met: bool
    passed: bool


def tally_votes(
    votes: Dict[str, bool],
    voters: Dict[str, Voter],
) -> Tuple[int, int, int]:
    """Return (votes_for, votes_against, total_possible_weight)."""
    for_weight = 0
    against_weight = 0
    total_weight = sum(v.weight for v in voters.values())
    for voter_id, choice in votes.items():
        weight = voters[voter_id].weight
        if choice:
            for_weight += weight
        else:
            against_weight += weight
    return for_weight, against_weight, total_weight


def evaluate_proposal(
    proposal: Proposal,
    voters: Dict[str, Voter],
    votes: Dict[str, bool],
) -> VoteResult:
    votes_for, votes_against, total_weight = tally_votes(votes, voters)
    participating_weight = votes_for + votes_against
    quorum_met = (participating_weight / total_weight) >= proposal.quorum if total_weight > 0 else False
    support = (votes_for / participating_weight) if participating_weight > 0 else 0.0
    passed = quorum_met and (support >= proposal.threshold)
    return VoteResult(
        votes_for=votes_for,
        votes_against=votes_against,
        total_possible_weight=total_weight,
        quorum_met=quorum_met,
        passed=passed,
    )


def simulate_votes_deterministic(
    voters: Dict[str, Voter],
    approve_voter_ids: List[str],
) -> Dict[str, bool]:
    """Deterministic simulator: specified voters vote True, others False."""
    return {vid: (vid in approve_voter_ids) for vid in voters}


def simulate_votes_random(
    voters: Dict[str, Voter],
    rng: random.Random,
    approval_probability: float = 0.6,
    participation_probability: float = 0.9,
) -> Dict[str, bool]:
    """Random simulator, seedable via provided rng.

    Returns only votes cast (participants); abstentions are omitted.
    """
    votes: Dict[str, bool] = {}
    for vid in voters:
        if rng.random() <= participation_probability:
            votes[vid] = rng.random() <= approval_probability
    return votes


