from __future__ import annotations

from sim.voting import Voter, Proposal, simulate_votes_deterministic, evaluate_proposal


def test_quorum_and_majority_pass():
    voters = {f"v{i}": Voter(voter_id=f"v{i}", weight=i) for i in range(1, 6)}  # total=15
    approve = ["v3", "v4", "v5"]  # weights 3+4+5=12
    votes = simulate_votes_deterministic(voters, approve)
    proposal = Proposal("p", "w1", "w2", quorum=0.5, threshold=0.5)
    res = evaluate_proposal(proposal, voters, votes)
    assert res.quorum_met is True  # 12/15 >= 0.5
    assert res.passed is True      # support 12/12 == 1.0


def test_quorum_fail():
    voters = {"a": Voter("a", 10), "b": Voter("b", 10)}  # total=20
    votes = {"a": True}  # participation=10/20=0.5 -> meets
    proposal = Proposal("p", "w1", "w2", quorum=0.6, threshold=0.5)
    res = evaluate_proposal(proposal, voters, votes)
    assert res.quorum_met is False
    assert res.passed is False


