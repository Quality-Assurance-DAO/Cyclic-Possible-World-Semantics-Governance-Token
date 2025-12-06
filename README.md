# Cyclic Possible World Semantics Governance Token (PWSGT) – Python Simulation

This repository provides a runnable Python 3.9+ simulation of a cyclic possible-world governance system with Kripke semantics, voting, token-like world metadata, simulated on-chain transitions (Cardano), off-chain storage placeholders (Arweave), and visualization.

## Quickstart

1) Create a virtualenv and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Initialize the example graph and worlds:

```bash
python scripts/init_graph.py
```

3) Run a voting simulation (deterministic with seed):

```bash
python scripts/run_vote_sim.py --seed 42
```

This produces `examples/worlds/*.json`, `examples/graph.json`, appends to `examples/history.json`, and updates `examples/active_world.json`.

4) Visualize:

```bash
python scripts/visualize.py
```

This generates `examples/graph.png` and `examples/timeline.png`.

5) Run tests:

```bash
pytest -q
```

## Streamlit Dashboard

Launch the interactive dashboard (multi-tab UI):

```bash
streamlit run dashboard/streamlit_app.py
```

Tabs:
- Overview: active world, transition count, init/reset actions
- Configure & Run: set seed/quorum/threshold/voters/probabilities and run predefined or custom proposals
- Graph: view the Kripke graph with active world highlighted
- Timeline: view transition history and a table of recent transitions
- Data: inspect and download JSON artifacts (`examples/`)

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

