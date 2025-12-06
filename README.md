# Cyclic Possible World Semantics Governance Token (PWSGT) – Python Simulation

This repository provides a runnable Python 3.9+ simulation of a cyclic possible-world governance system with Kripke semantics, voting, token-like world metadata, simulated on-chain transitions (Cardano), off-chain storage placeholders (Arweave), and visualization.

## Understanding the Core Concepts

This section explains the key academic terms used in this project in novice-friendly language, establishing their real-world utility for DAO governance.

| Technical Term | Novice-Friendly Analogy/Explanation |
|----------------|--------------------------------------|
| **Possible World** | A defined state or a future version of the DAO/protocol (e.g., "World A has Feature X activated," "World B has Parameter Y set to 10"). Each world represents a specific configuration of governance rules, features, and parameters. Think of it as a snapshot of how the DAO is configured at a particular point in time. |
| **Kripke Semantics / Accessibility Relation** | The "Rulebook" or "Roadmap" that defines which state (World) can legally follow another. An edge from W1 to W2 means W2 is a possible transition from W1. This creates a graph structure showing all valid paths the governance system can take. Just like a roadmap shows which cities you can travel to from your current location, the accessibility relation shows which governance states you can transition to from your current state. |
| **Cyclic** | The system can revisit or correct past states. Governance is not a linear path; a DAO can always loop back to a previous configuration if needed, reflecting the philosophy of governance as a continuous loop. This means if a new governance change doesn't work out, the community can vote to revert to a previous, proven configuration. The cyclic structure acknowledges that governance is iterative and that sometimes going "backwards" is the right forward move. |

### Why This Matters for Real-World DAO Governance

- **Possible Worlds** enable **version control for governance**: Just like software can have different versions, DAOs can have different governance configurations. Each world represents a tested, documented state that can be referenced and returned to.

- **Accessibility Relations** provide **constitutional constraints**: Not every governance change should be possible from every state. The accessibility relation ensures that transitions follow logical rules and prevent invalid or dangerous state changes.

- **Cyclic structure** supports **governance flexibility**: Real governance systems need the ability to correct mistakes, revert changes, and iterate on solutions. The cyclic model reflects this reality, allowing DAOs to learn from experience and adapt.

## Quickstart

The **Streamlit Dashboard** is the most intuitive interface for exploring the simulation. It provides immediate visual feedback and is the recommended starting point.

### Step 1: Setup

Create a virtualenv and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Launch the Dashboard

Start the interactive Streamlit dashboard:

```bash
streamlit run dashboard/streamlit_app.py
```

The dashboard will open in your browser automatically.

### Step 3: Initialize the Example Graph

1. Go to the **Overview** tab
2. Click **"Initialize Example Graph"** button
   - This creates the example worlds (w1, w2, w3, w4) and sets up the initial state

### Step 4: Run a Simulation

1. Go to the **Configure & Run** tab
2. Ensure the **Seed** is set (default: 42)
3. Adjust parameters if desired (quorum, threshold, approval probability, etc.)
4. Click **"Run Vote Simulation"** button
   - The simulation will process proposals and update the active world based on voting results
   - Watch the **Simulation Log** for detailed information about each proposal

### Step 5: View Results

1. Go to the **Graph** tab to see:
   - The Kripke model visualization with nodes colored by state (active/visited/unvisited)
   - World labels showing which propositions are true in each world
   - The current active world highlighted in yellow

2. Go to the **Timeline** tab to see:
   - A visual timeline of all successful transitions
   - A table showing detailed information about each transition

3. Go to the **Data** tab to inspect:
   - Raw JSON files (active_world.json, history.json, valuation.json, etc.)
   - A truth table showing which propositions are true in each world

### Dashboard Tabs Overview

- **Overview**: Active world status, transition count, and initialization/reset actions
- **Configure & Run**: Set seed/quorum/threshold/voters/probabilities and run predefined or custom proposals
- **Graph**: View the Kripke graph with active world highlighted and world names displayed
- **Timeline**: View transition history and a table of recent transitions
- **Data**: Inspect and download JSON artifacts (`examples/`)

## Command-Line Interface (Alternative)

If you prefer command-line tools, you can also use the CLI scripts:

1) Initialize the example graph and worlds:

```bash
python scripts/init_graph.py
```

2) Run a voting simulation (deterministic with seed):

```bash
python scripts/run_vote_sim.py --seed 42
```

This produces `examples/worlds/*.json`, `examples/graph.json`, appends to `examples/history.json`, and updates `examples/active_world.json`.

3) Visualize:

```bash
python scripts/visualize.py
```

This generates `examples/graph.png` and `examples/timeline.png`.

4) Run tests:

```bash
pytest -q
```

### Deploy to Streamlit Community Cloud (JSON-only)

1) Fork this repo on GitHub.
2) In Streamlit Cloud, create a new app pointing to your fork and set the entrypoint to `dashboard/streamlit_app.py`.
3) Deploy. The app reads/writes JSON under `examples/` on the app filesystem.

Notes:
- Streamlit Cloud’s filesystem is ephemeral; data may reset on redeploy/restart. This version intentionally uses JSON-only, no external DB.
- Use the Overview tab’s “Initialize Example Graph” to (re)create example data.

#### Useful Streamlit links
- Streamlit Community Cloud (create app): https://share.streamlit.io
- Deployment guide: https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app
- App entrypoint settings: https://docs.streamlit.io/streamlit-community-cloud/manage-your-app#edit-app-settings
- Secrets management: https://docs.streamlit.io/streamlit-community-cloud/get-started/deploy-an-app/connect-to-data-sources/secrets-management
- App sharing and updates: https://docs.streamlit.io/streamlit-community-cloud/manage-your-app#share-your-app

## Interactive Controls: Understanding Quorum and Approval Thresholds

The dashboard's **Configure & Run** tab provides interactive controls that directly affect the probability of successful governance transitions. Understanding these parameters is crucial for predicting and controlling proposal outcomes.

### How Proposals Succeed or Fail

A proposal must pass **two independent checks** to succeed:

1. **Quorum Check**: Enough total voting weight must participate
2. **Approval Threshold Check**: Enough participating votes must be "for" the proposal

If either check fails, the proposal fails and the active world remains unchanged.

### Quorum: The Participation Requirement

**What it is**: The minimum fraction of total voting weight that must participate in the vote.

**How it works**:
- **Quorum = 0.5 (50%)**: At least 50% of all possible voting weight must participate
- **Quorum = 0.3 (30%)**: At least 30% of all possible voting weight must participate
- **Quorum = 0.8 (80%)**: At least 80% of all possible voting weight must participate

**Impact on success probability**:
- **Lower quorum** (e.g., 0.3) = **Higher success rate**: Easier to meet participation requirement
- **Higher quorum** (e.g., 0.8) = **Lower success rate**: Harder to get enough voters to participate

**Example**: With 10 voters (weights 1-10, total weight = 55):
- Quorum 0.5: Need at least 27.5 weight participating (e.g., voters 6-10 = 6+7+8+9+10 = 40 ✓)
- Quorum 0.8: Need at least 44 weight participating (e.g., voters 7-10 = 7+8+9+10 = 34 ✗, need more)

**Real-world analogy**: Quorum is like requiring a minimum number of board members to be present before a vote can be valid. Lower quorum = easier to hold a valid vote.

### Approval Threshold: The Support Requirement

**What it is**: The minimum fraction of **participating** voting weight that must vote "for" the proposal.

**How it works**:
- **Threshold = 0.5 (50%)**: More than 50% of participating weight must vote "for" (strict majority)
- **Threshold = 0.3 (30%)**: More than 30% of participating weight must vote "for" (super-majority)
- **Threshold = 0.7 (70%)**: More than 70% of participating weight must vote "for" (consensus)

**Important**: The threshold requires a **strict majority** (support > threshold), not equal to. A 50/50 tie fails when threshold = 0.5.

**Impact on success probability**:
- **Lower threshold** (e.g., 0.3) = **Higher success rate**: Easier to get enough "for" votes
- **Higher threshold** (e.g., 0.7) = **Lower success rate**: Harder to get enough "for" votes

**Example**: With 40 weight participating:
- Threshold 0.5: Need more than 20 weight voting "for" (e.g., 22 for, 18 against = 55% support ✓)
- Threshold 0.5: 20 for, 20 against = 50% support ✗ (tie fails, needs >50%)
- Threshold 0.7: Need more than 28 weight voting "for" (e.g., 25 for, 15 against = 62.5% support ✗, needs >70%)

**Real-world analogy**: Approval threshold is like requiring a supermajority vote. Lower threshold = easier to pass, higher threshold = requires more consensus.

### Interactive Control Strategy

**To increase proposal success rate**:
1. **Lower Quorum** (e.g., 0.3 instead of 0.5): Makes it easier to meet participation requirement
2. **Lower Approval Threshold** (e.g., 0.4 instead of 0.5): Makes it easier to get enough "for" votes
3. **Increase Approval Probability** (e.g., 0.8 instead of 0.6): Each voter is more likely to vote "for"
4. **Increase Participation Probability** (e.g., 0.98 instead of 0.95): More voters participate, making quorum easier

**To decrease proposal success rate** (require more consensus):
1. **Raise Quorum** (e.g., 0.7): Requires more participation
2. **Raise Approval Threshold** (e.g., 0.7): Requires stronger consensus among participants
3. **Lower Approval Probability** (e.g., 0.4): Each voter is less likely to vote "for"

### Visual Feedback in the Dashboard

The **Simulation Log** in the Configure & Run tab shows exactly why each proposal succeeded or failed:

- **Success**: Shows vote counts and confirms both quorum and threshold were met
- **Failure**: Shows which requirement failed:
  - `Quorum not met (X% < Y%)`: Not enough participation
  - `Threshold not met (X% ≤ Y%)`: Not enough "for" votes (or tie)

**Experiment tip**: Try running the same simulation with different quorum/threshold values and compare the results in the Simulation Log to see how these parameters directly affect outcomes.

## Repository Layout

- `sim/` – core simulation modules
  - `model.py` – `World`, `Transition`, `KripkeModel`, and modal evaluation (□/◇)
  - `graph_store.py` – NetworkX wrapper for loading/saving worlds and graph analytics
  - `voting.py` – proposals, weighted voting, thresholds, simulators
  - `tokenize.py` – CIP-25-like NFT metadata generation for worlds
  - `archiver.py` – mock Arweave uploader + commented real-client hooks
  - `cardano_sim.py` – simulated Cardano tx builder and active-world registry
  - `visualize.py` – graph and timeline plotting utilities
- `scripts/` – runnable CLI scripts
  - `init_graph.py`, `run_vote_sim.py`, `visualize.py`
- `examples/` – world JSONs, history, active world, and generated images
- `tests/` – pytest unit tests for modal logic, voting, and graph ops

## Simulated vs Real Integrations

- Arweave: `sim/archiver.py` has a deterministic mock uploader that returns `ar://placeholder-<hash>`. To attach a real Arweave wallet, insert your JWK and uncomment the indicated client code.
- Cardano: `sim/cardano_sim.py` records simulated transition transactions into JSON (`examples/history.json`) and maintains a single-file `examples/active_world.json` registry. Hooks are provided (commented) showing where to integrate `pycardano` signing and Blockfrost submission.

## Example Scenario

- Worlds: `w1..w4` with valuations for `p1..p4` and edges: `(w1→w2)`, `(w2→w3)`, `(w3→w4)`, `(w4→w1)`, `(w2→w1)`, `(w3→w2)`.
- **Forward proposals** (cycle-advancing): `prop-001-forward` (w1→w2), `prop-002-forward` (w2→w3), `prop-003-forward` (w3→w4), `prop-004-forward` (w4→w1). These demonstrate forward progression through the cyclic possible world model.
- **Reverse proposals** (cycle-reversing): `prop-005-reverse` (w2→w1), `prop-006-reverse` (w3→w2). These demonstrate that transitions can go backwards, highlighting the cyclic and reversible nature of possible worlds.
- Voters: 10 voters with weights 1..10. Default thresholds: quorum 0.5, majority 0.5.

### Demonstrating Cyclic Nature

The simulation demonstrates the **cyclic nature of possible worlds** through:
1. **Forward cycle**: Proposals advance through w1→w2→w3→w4→w1, completing a full cycle
2. **Reverse transitions**: Proposals can go backwards (w2→w1, w3→w2), showing reversibility
3. **Cyclic structure**: The world graph forms a cycle, allowing governance to return to previous states

## Understanding Proposal Success and Failure

Proposals can **fail** even when they match the current active world. A proposal fails if:

1. **Quorum not met**: Not enough voting weight participates (participation < quorum threshold)
2. **Threshold not met**: Even with quorum, not enough participating votes are "for" (support ≤ approval threshold)

**Important**: The approval threshold requires a **strict majority** (support > threshold), not just equal to the threshold. This means:
- With threshold=0.5 (50%), a 50/50 tie (22 for, 22 against) will **fail** because 50% is not greater than 50%
- A proposal needs **more than 50%** support to pass (e.g., 23 for, 21 against = 52.3% support passes)
- This ensures that ties fail and only clear majorities pass

### Why Proposals Fail

The simulation uses **random voting** (seedable for reproducibility). Even with high approval probability, some proposals may fail due to random chance. This is expected behavior and reflects real-world governance where proposals don't always pass.

### Adjusting Parameters to Increase Success Rate

To get more proposals to pass:

- **Increase Approval Probability** (default 0.6): Higher chance each voter votes "for"
- **Lower Approval Threshold** (default 0.5): Requires less support to pass (e.g., 0.4 = 40% support needed)
- **Lower Quorum** (default 0.5): Requires less participation (e.g., 0.3 = 30% participation needed)
- **Try Different Seeds**: Different random seeds produce different voting patterns

### Proposal Execution Flow

1. Proposals are processed **sequentially** in the order specified
2. Each proposal checks if the **current active world** matches its `from_world`
3. If matched, the proposal runs a vote simulation
4. If the vote **passes** (quorum + threshold met), the active world transitions to `to_world`
5. If the vote **fails**, the active world **stays unchanged**
6. Subsequent proposals that don't match the current active world are **skipped**

**Example**: If prop-004 (w4→w1) fails, the active world remains w4, so prop-005 (w2→w1) and prop-006 (w3→w2) will be skipped because they require w2 and w3 respectively, not w4.

## Moving to Real Cardano + Arweave

- Arweave
  - Add your wallet JWK path to `sim/archiver.py` and uncomment the noted section.
  - Replace `MockArchiver.upload_json` with the real client upload, capturing the returned transaction id (arweave txid).

- Cardano (testnet)
  - Install `pycardano` and set a Blockfrost testnet API key.
  - In `sim/cardano_sim.py`, replace the simulated transaction builder with a real `pycardano` transaction, sign with your key, and submit via Blockfrost.
  - Use the returned tx hash in `history.json` and `active_world.json`.

Security note: Never commit private keys/JWKs to the repo. Use environment variables or a secure secrets manager.

## Troubleshooting

- Ensure you are in the virtualenv and dependencies are installed.
- If images don't appear, ensure you have a non-interactive Matplotlib backend (default works for PNG generation).
- Re-run `init_graph.py` to regenerate the example worlds and graph summary.
- **Only seeing 3 proposals succeed?** This is normal if later proposals fail due to voting results. Check the simulation log for detailed failure reasons. Increase approval probability or lower thresholds to increase success rate.
- **Proposals being skipped?** A proposal is skipped if the current active world doesn't match its `from_world`. This happens when a previous proposal failed, leaving the active world unchanged.

## License

MIT

