from __future__ import annotations

import io
import json
import os
import random
import sys
import time
from typing import Dict

import streamlit as st

# Ensure project root is importable
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from sim.sim_helpers import (
    ensure_examples_dirs,
    load_worlds_and_valuation,
    default_proposals,
    build_voters,
    run_single_proposal,
)
from sim.model import KripkeModel
from sim.visualize import graph_png_bytes, timeline_png_bytes
from scripts.init_graph import main as init_graph_script


st.set_page_config(page_title="PWSGT Dashboard", layout="wide")
st.title("PWSGT – Cyclic Possible World Governance (Simulation)")

root = ROOT
examples_dir, worlds_dir = ensure_examples_dirs(root)


def read_active():
    path = os.path.join(examples_dir, "active_world.json")
    if not os.path.exists(path):
        return {"active_world": "w1", "last_tx": None, "updated_at": None}
    return json.load(open(path, 'r', encoding='utf-8'))


def read_history():
    path = os.path.join(examples_dir, "history.json")
    if not os.path.exists(path):
        return []
    return json.load(open(path, 'r', encoding='utf-8'))


def reset_history():
    history_path = os.path.join(examples_dir, "history.json")
    active_path = os.path.join(examples_dir, "active_world.json")
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump([], f)
    with open(active_path, 'w', encoding='utf-8') as f:
        json.dump({"active_world": "w1", "last_tx": None, "updated_at": None}, f)


tab_overview, tab_run, tab_graph, tab_timeline, tab_data = st.tabs([
    "Overview", "Configure & Run", "Graph", "Timeline", "Data",
])


with tab_overview:
    st.markdown(
        """
        This dashboard simulates a cyclic possible-worlds governance model. Use the tabs to configure voters and thresholds, run proposals, and visualize the resulting state transitions.

        """
    )
    with st.expander("Key terms (what things mean)"):
        st.markdown(
            """
            - **World**: An immutable governance configuration (node) identified by a `world_id` (e.g., `w1`).
            - **Transition**: A directed change from one world to another (edge), optionally cyclic.
            - **Active world**: The current world in effect; updated after a passed proposal (in simulation, stored in `examples/active_world.json`).
            - **Kripke model**: A graph (worlds + edges) with a valuation of propositions that can be checked with modal operators.
            - **□p (Necessary)**: True at world `w` if proposition `p` is true in all successors of `w`.
            - **◇p (Possible)**: True at world `w` if proposition `p` is true in at least one successor of `w`.
            - **Quorum**: Minimum fraction of total voting weight that must participate for a proposal to be valid.
            - **Approval threshold**: Fraction of participating weight that must vote "for" to pass (e.g., 0.5 = simple majority).
            - **Voter weight**: The voting power assigned to a voter (here, integers 1..N by default).
            - **History**: The sequence of simulated transition transactions written to `examples/history.json`.
            """
        )
    col1, col2, col3 = st.columns(3)
    active = read_active()
    history = read_history()
    col1.metric("Active World", active.get("active_world"))
    col2.metric("Transitions", len(history))
    col3.metric("Last TX", active.get("last_tx") or "—")

    st.subheader("Quick Actions")
    c1, c2 = st.columns(2)
    if c1.button("Initialize Example Graph", use_container_width=True):
        init_graph_script()
        st.success("Initialized worlds and graph in examples/.")
    if c2.button("Reset History", use_container_width=True):
        reset_history()
        st.session_state.history_reset = True
        st.session_state.refresh_counter = st.session_state.get("refresh_counter", 0) + 1
        st.rerun()
    
    if st.session_state.get("history_reset", False):
        st.success("Cleared history and reset active world.")
        st.session_state.history_reset = False


with tab_run:
    st.markdown(
        """
        Configure simulation parameters and run proposals. You can run predefined sequences or submit custom proposals.
        """
    )
    with st.expander("Parameters explained"):
        st.markdown(
            """
            - **Seed**: Random number generator seed for reproducible simulations.
            - **Quorum**: Minimum fraction of total voting weight that must participate (e.g., 0.5 = 50%).
            - **Approval threshold**: Fraction of participating weight that must vote "for" to pass (e.g., 0.5 = simple majority).
            - **Approval probability**: Chance each participating voter votes "for" (0.6 = 60%).
            - **Participation probability**: Chance each voter participates at all (0.95 = 95%).
            - **Voters**: Number of simulated voters with weights 1, 2, 3, ..., N.
            - **Run N predefined proposals**: Execute the first N proposals from the example sequence (w1→w2, w2→w3, w3→w4, w4→w1, w2→w1, w3→w2).
            """
        )
    st.subheader("Parameters")
    with st.form("run_form"):
        seed = st.number_input("Seed", value=42, step=1)
        quorum = st.slider("Quorum", 0.0, 1.0, 0.5, 0.05)
        threshold = st.slider("Approval threshold", 0.0, 1.0, 0.5, 0.05)
        approval_prob = st.slider("Approval probability", 0.0, 1.0, 0.6, 0.05)
        participation_prob = st.slider("Participation probability", 0.0, 1.0, 0.95, 0.05)
        voter_count = st.number_input("Voters", value=10, step=1, min_value=1, max_value=100)
        n_steps = st.number_input("Run N predefined proposals", value=6, step=1, min_value=1, max_value=20)
        clear_history = st.checkbox("Clear history before running", value=True, 
                                   help="If checked, resets history and active world to initial state before running the simulation")
        submitted = st.form_submit_button("Run Simulation")

    if submitted:
        # Clear history if requested
        if clear_history:
            reset_history()
        rng = random.Random(int(seed))
        voters = build_voters(int(voter_count))
        proposals = default_proposals()[: int(n_steps)]
        last_result = None
        for prop_id, src, dst in proposals:
            tx, result = run_single_proposal(
                examples_dir=examples_dir,
                proposal_id=prop_id,
                from_world=src,
                to_world=dst,
                quorum=float(quorum),
                threshold=float(threshold),
                rng=rng,
                approval_probability=float(approval_prob),
                participation_probability=float(participation_prob),
                voters=voters,
            )
            last_result = (prop_id, src, dst, tx, result)
        if last_result:
            prop_id, src, dst, tx, result = last_result
            if tx is None:
                st.warning(f"Last proposal {prop_id} {src}->{dst} failed. Quorum={result.quorum_met}")
            else:
                st.success(f"Last TX {tx.tx_id}: {src}->{dst} passed.")
        st.session_state.refresh_counter = st.session_state.get("refresh_counter", 0) + 1
        st.rerun()

    st.divider()
    st.subheader("Run Custom Proposal")
    store, worlds, model = load_worlds_and_valuation(examples_dir)
    world_ids = sorted(worlds.keys())
    c1, c2, c3 = st.columns(3)
    from_w = c1.selectbox("From world", world_ids, index=0)
    to_w = c2.selectbox("To world", [w for w in world_ids if w != from_w], index=0)
    prop_id_custom = c3.text_input("Proposal ID", value="prop-custom")
    if st.button("Run Proposal"):
        rng = random.Random(int(seed))
        voters = build_voters(int(voter_count))
        tx, result = run_single_proposal(
            examples_dir=examples_dir,
            proposal_id=prop_id_custom,
            from_world=from_w,
            to_world=to_w,
            quorum=float(quorum),
            threshold=float(threshold),
            rng=rng,
            approval_probability=float(approval_prob),
            participation_probability=float(participation_prob),
            voters=voters,
        )
        if tx is None:
            st.warning(f"Proposal failed. Quorum={result.quorum_met}")
        else:
            st.success(f"TX {tx.tx_id}: {from_w}->{to_w} passed.")
        st.session_state.refresh_counter = st.session_state.get("refresh_counter", 0) + 1
        st.rerun()


with tab_graph:
    st.markdown(
        """
        View the Kripke model as a directed graph. The active world is highlighted in yellow.
        """
    )
    with st.expander("Graph elements"):
        st.markdown(
            """
            - **Nodes (circles)**: Worlds (w1, w2, w3, w4) with their truth assignments shown as {p1, p2, ...}.
            - **Edges (arrows)**: Possible transitions between worlds.
            - **Yellow node**: The currently active world.
            - **Blue nodes**: Other worlds.
            - **Layout**: Spring layout (may vary on refresh).
            """
        )
    # Force refresh by including refresh counter in computation
    _ = st.session_state.get("refresh_counter", 0)
    store, worlds, model = load_worlds_and_valuation(examples_dir)
    props = sorted(list(model.valuation.keys()))
    labels = {w: model.summarize_world_label(w, props) for w in worlds}
    active = read_active().get("active_world", "w1")
    st.image(graph_png_bytes(store.G, active, labels))


with tab_timeline:
    st.markdown(
        """
        View the sequence of transitions over time. Each point represents a successful transition to a new world.
        """
    )
    with st.expander("Timeline elements"):
        st.markdown(
            """
            - **X-axis**: Transition number (chronological order).
            - **Y-axis**: World IDs (w1, w2, w3, w4).
            - **Points**: Each successful transition, labeled with the destination world.
            - **Table below**: Detailed transaction records with votes, quorum, timestamps.
            """
        )
    # Force refresh - read history fresh each time
    refresh_counter = st.session_state.get("refresh_counter", 0)
    history = read_history()
    history_count = len(history)
    
    # Get file modification time to detect changes
    history_path = os.path.join(examples_dir, "history.json")
    file_mtime = 0
    if os.path.exists(history_path):
        file_mtime = os.path.getmtime(history_path)
    
    # Create signature that changes with history content and file modification
    history_signature = f"{history_count}_{refresh_counter}_{file_mtime}"
    if history:
        # Include last few proposal IDs in signature for uniqueness
        last_props = "_".join([h.get("proposal_id", "") for h in history[-3:]])
        history_signature += f"_{hash(last_props)}"
    
    # Force Streamlit to recognize this as a new computation
    _ = history_signature
    
    # Always read from file and regenerate timeline
    tl_bytes = timeline_png_bytes(history_path)
    
    if tl_bytes:
        # Display image - Streamlit should regenerate due to signature change
        st.image(tl_bytes, use_container_width=True)
    else:
        st.info("No timeline yet. Run a simulation to generate transitions.")
    data = history
    if data:
        st.dataframe(data, use_container_width=True, hide_index=True)


with tab_data:
    st.markdown(
        """
        Inspect the raw JSON artifacts that store the simulation state and history.
        """
    )
    with st.expander("Data files explained"):
        st.markdown(
            """
            - **active_world.json**: Current active world, last transaction ID, and timestamp.
            - **valuation.json**: Truth table showing which propositions (p1, p2, p3, p4) are true in each world.
            - **graph.json**: Graph structure (nodes, edges, cycles) computed from world definitions.
            - **history.json**: Complete log of all transition transactions with votes, quorum, and metadata.
            - **worlds/*.json**: Individual world definitions with metadata, edges, and Arweave URI placeholders.
            """
        )
    st.subheader("Artifacts")
    colA, colB = st.columns(2)
    with colA:
        st.write("active_world.json")
        st.json(read_active())
        st.write("valuation.json")
        val_path = os.path.join(examples_dir, "valuation.json")
        if os.path.exists(val_path):
            st.json(json.load(open(val_path, 'r', encoding='utf-8')))
        else:
            st.info("No valuation.json yet. Initialize the graph.")
    with colB:
        st.write("graph.json")
        graph_path = os.path.join(examples_dir, "graph.json")
        if os.path.exists(graph_path):
            st.json(json.load(open(graph_path, 'r', encoding='utf-8')))
        else:
            st.info("No graph.json yet. Initialize the graph.")
    st.write("history.json")
    st.json(read_history())


