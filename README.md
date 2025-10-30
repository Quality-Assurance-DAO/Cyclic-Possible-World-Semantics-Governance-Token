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
- Proposals simulate enabling quorum, delegation, council creation, reset, and two reverse moves.
- Voters: 10 voters with weights 1..10. Default thresholds: quorum 0.5, majority 0.5.

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
- If images don’t appear, ensure you have a non-interactive Matplotlib backend (default works for PNG generation).
- Re-run `init_graph.py` to regenerate the example worlds and graph summary.

## License

MIT

