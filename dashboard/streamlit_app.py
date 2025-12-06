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
    all_six_proposals_sequence,
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
    # Force a fresh read by opening and closing the file explicitly
    # and potentially retrying if file is locked
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except (IOError, OSError, json.JSONDecodeError) as e:
        # If there's an error, wait a tiny bit and retry once
        time.sleep(0.01)
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)


def read_history():
    path = os.path.join(examples_dir, "history.json")
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def reset_history():
    """Reset history and active world to initial state (w1)."""
    history_path = os.path.join(examples_dir, "history.json")
    active_path = os.path.join(examples_dir, "active_world.json")
    # Clear history
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump([], f)
        f.flush()
        os.fsync(f.fileno())
    # Reset active world to w1 (default/initial state)
    with open(active_path, 'w', encoding='utf-8') as f:
        json.dump({"active_world": "w1", "last_tx": None, "updated_at": None}, f)
        f.flush()
        os.fsync(f.fileno())


def format_world_label(world_id: str, worlds: Dict = None) -> str:
    """Format world ID with its name for display.
    
    Args:
        world_id: The world ID (e.g., "w1")
        worlds: Optional dict of World objects keyed by world_id. If None, will load from examples_dir.
    
    Returns:
        Formatted string like "w1 (Base Governance)" or just "w1" if world not found.
    """
    if worlds is None:
        try:
            _, worlds_dict, _ = load_worlds_and_valuation(examples_dir)
            worlds = worlds_dict
        except Exception:
            return world_id
    
    if world_id in worlds:
        world = worlds[world_id]
        return f"{world_id} ({world.name})"
    return world_id


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
            - **World**: An immutable governance configuration (node) identified by a `world_id` (e.g., `w1`). Each world represents a specific state of the DAO/protocol with defined rules, features, and parameters. Think of it as a snapshot of how the DAO is configured at a particular point in time.
            
            - **Transition**: A directed change from one world to another (edge), optionally cyclic. A transition represents a governance proposal that moves the system from one state to another.
            
            - **Active world**: The current world in effect; updated after a passed proposal (in simulation, stored in `examples/active_world.json`). This is the governance state currently in use.
            
            - **Kripke model**: A graph (worlds + edges) with a valuation of propositions that can be checked with modal operators. The model defines all possible states (worlds) and which transitions between them are allowed (accessibility relation). It provides a formal way to reason about what governance states are possible and which transitions are valid.
            
            - **Accessibility Relation**: The "rulebook" or "roadmap" that defines which state (World) can legally follow another. An edge from W1 to W2 means W2 is a possible transition from W1. This creates the graph structure showing all valid governance paths. Just like a roadmap shows which cities you can travel to from your current location, the accessibility relation shows which governance states you can transition to from your current state.
            
            - **Cyclic**: The system can revisit or correct past states. Governance is not a linear path; a DAO can always loop back to a previous configuration if needed, reflecting the philosophy of governance as a continuous loop. This means if a new governance change doesn't work out, the community can vote to revert to a previous, proven configuration.
            
            - **Quorum**: The minimum percentage of total voting weight that must participate for a vote to be considered valid. Example: 0.5 = 50% of all voters must participate. If quorum isn't met, the proposal fails regardless of how the votes are distributed. Lower values make it easier to meet the participation requirement.
            
            - **Approval threshold**: The minimum percentage of participating voting weight that must vote "for" to pass (e.g., 0.5 = simple majority). Requires strict majority (support > threshold), so a 50/50 tie fails when threshold is 0.5. Lower values make proposals easier to pass.
            
            - **□p (Necessary)**: True at world `w` if proposition `p` is true in all successors of `w`. Represents a requirement that must hold in all possible next states.
            
            - **◇p (Possible)**: True at world `w` if proposition `p` is true in at least one successor of `w`. Represents a possibility that can be achieved in some future state.
            
            - **Voter weight**: The voting power assigned to a voter (here, integers 1..N by default). Higher weight voters have more influence in the voting process.
            
            - **History**: The sequence of simulated transition transactions written to `examples/history.json`. This records all successful governance transitions with their vote counts, timestamps, and metadata.
            """
        )
    col1, col2, col3 = st.columns(3)
    active = read_active()
    history = read_history()
    # Load worlds to get names for display
    try:
        _, worlds_dict, _ = load_worlds_and_valuation(examples_dir)
        active_world_id = active.get("active_world", "w1")
        active_world_label = format_world_label(active_world_id, worlds_dict)
    except Exception:
        active_world_label = active.get("active_world", "w1")
    col1.metric("Active World", active_world_label)
    col2.metric("Transitions", len(history))
    col3.metric("Last TX", active.get("last_tx") or "—")

    st.subheader("Quick Actions")
    c1, c2 = st.columns(2)
    if c1.button("Initialize Example Graph", use_container_width=True):
        init_graph_script()
        st.success("Initialized worlds and graph in examples/.")
    if c2.button("Reset History", use_container_width=True):
        reset_history()
        # Verify reset worked - active world should always be w1 after reset
        verify_active = read_active().get("active_world", "w1")
        verify_history = read_history()
        if verify_active == "w1" and len(verify_history) == 0:
            st.success(f"Cleared history and reset active world to w1 (default initial state).")
        else:
            st.error(f"Reset may have failed. Active world: {verify_active} (expected w1), History entries: {len(verify_history)}")
        st.session_state.history_reset = True
        st.session_state.refresh_counter = st.session_state.get("refresh_counter", 0) + 1
        st.rerun()
    
    if st.session_state.get("history_reset", False):
        # Message already shown above
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
            - **Seed**: Random number generator seed for reproducible simulations. Different seeds produce different voting patterns. Same seed = same results.
            
            - **Quorum**: The minimum percentage of total voting weight that must participate for a vote to be considered valid (e.g., 0.5 = 50%). If quorum isn't met, the proposal fails regardless of how the votes are distributed. Lower quorum = easier to meet participation requirement.
            
            - **Approval threshold**: The minimum percentage of participating voting weight that must vote "for" to pass (e.g., 0.5 = simple majority). **Requires strict majority** (support > threshold), so a 50/50 tie fails. Even with quorum, if support is at or below this threshold, the proposal fails. Lower threshold = easier to pass.
            
            - **Approval probability**: The chance each participating voter votes "for" (0.6 = 60%). Higher values increase the likelihood of proposals passing. This simulates voter sentiment toward the proposal.
            
            - **Participation probability**: The chance each voter participates at all (0.95 = 95%). Lower values reduce total participation, making quorum harder to meet. This simulates voter engagement.
            
            - **Voters**: Number of simulated voters with weights 1, 2, 3, ..., N. Total voting weight = sum of all weights. Higher weight voters have more influence.
            
            - **Run N predefined proposals**: Execute the first N proposals from the selected sequence. Proposals run sequentially and may be skipped if the active world doesn't match.
            
            - **Proposal sequence**: Choose between default sequence (4 forward proposals that complete the cycle) or interleaved sequence (all 6 proposals including reverse transitions, requires 8 proposals total to reach w4).
            
            **Proposal Types:**
            - **Forward proposals** (prop-001 through prop-004): Advance through the cycle w1→w2→w3→w4→w1, demonstrating forward progression in the cyclic possible world model.
            - **Reverse proposals** (prop-005, prop-006): Reverse the cycle (w2→w1, w3→w2), demonstrating that transitions can go backwards, highlighting the cyclic and reversible nature of possible worlds.
            - **Guaranteed approval mode**: When enabled, all proposals that match the active world automatically pass (bypasses voting). Useful for testing state transitions without worrying about vote failures.
            
            **Understanding Proposal Success:**
            - Proposals can **fail** even when they match the current active world. This happens when voting results don't meet quorum or threshold requirements.
            - If a proposal **fails**, the active world **stays unchanged**, so subsequent proposals that don't match will be **skipped**.
            - To increase success rate: raise approval probability, lower approval threshold, or lower quorum.
            - **For guaranteed success**: Enable "Guaranteed approval mode" to automatically approve all matching proposals (useful for testing all 6 proposals in sequence).
            - Check the **Simulation Log** below for detailed vote counts and failure reasons.
            """
        )
    st.subheader("Parameters")
    # Guaranteed approval mode is outside form so it's accessible for custom proposals too
    guaranteed_approval = st.checkbox("Guaranteed approval mode", value=False,
                                     help="If enabled, all proposals that match the active world will automatically pass (bypasses voting). Useful for testing state transitions.")
    with st.form("run_form"):
        seed = st.number_input("Seed", value=42, step=1, help="Random number generator seed for reproducible simulations. Different seeds produce different voting patterns.")
        quorum = st.slider("Quorum", 0.0, 1.0, 0.5, 0.05, 
                          help="The minimum percentage of total voting weight that must participate for a vote to be considered valid. Example: 0.5 = 50% of all voters must participate. Lower values make it easier to meet the participation requirement.")
        threshold = st.slider("Approval threshold", 0.0, 1.0, 0.5, 0.05,
                             help="The minimum percentage of participating voting weight that must vote 'for' to pass. Requires strict majority (support > threshold), so a 50/50 tie fails when threshold is 0.5. Lower values make proposals easier to pass.")
        approval_prob = st.slider("Approval probability", 0.0, 1.0, 0.6, 0.05,
                                 help="The probability that each participating voter will vote 'for' the proposal. Higher values increase the likelihood of proposals passing. Example: 0.6 = 60% chance each voter approves.")
        participation_prob = st.slider("Participation probability", 0.0, 1.0, 0.95, 0.05,
                                      help="The probability that each voter will participate in the vote at all. Lower values reduce total participation, making quorum harder to meet. Example: 0.95 = 95% chance each voter participates.")
        voter_count = st.number_input("Voters", value=10, step=1, min_value=1, max_value=100,
                                     help="Number of simulated voters. Each voter has a weight (1, 2, 3, ..., N). Total voting weight = sum of all voter weights.")
        # Proposal sequence selection
        proposal_sequence = st.radio(
            "Proposal sequence",
            ["Default (forward cycle + reverse)", "All 6 proposals (interleaved)"],
            help="Default: 4 forward proposals (w1→w2→w3→w4→w1) complete the cycle, then 2 reverse proposals (only 4 can run). All 6: interleaved sequence demonstrating both forward and reverse transitions in the cyclic model (requires 8 proposals to reach all worlds including w4)."
        )
        # Get the actual number of available proposals based on selected sequence
        if proposal_sequence == "All 6 proposals (interleaved)":
            all_proposals_list = all_six_proposals_sequence()
            default_steps = 8  # Need all 8 to reach w4
            st.info("ℹ️ **Interleaved sequence note**: This sequence has 8 proposals total. You need to run all 8 proposals to reach w4. The default is set to 8.")
        else:
            all_proposals_list = default_proposals()
            default_steps = 6
        available_proposals = len(all_proposals_list)
        filter_matching_only = st.checkbox("Show only matching proposals", value=False,
                                          help="If enabled, only proposals that match the current active world will be included in the run list. This filters out proposals that would be skipped.")
        
        # Show preview of matching proposals if filter is enabled
        if filter_matching_only:
            try:
                _, worlds_preview, _ = load_worlds_and_valuation(examples_dir)
            except Exception:
                worlds_preview = {}
            current_active_preview = read_active().get("active_world", "w1")
            current_active_preview_label = format_world_label(current_active_preview, worlds_preview)
            matching_preview = [(pid, src, dst) for pid, src, dst in all_proposals_list if src == current_active_preview]
            if matching_preview:
                matching_ids = [p[0] for p in matching_preview]
                st.info(f"📋 Filter active: {len(matching_preview)} proposal(s) match current active world ({current_active_preview_label}): {matching_ids}")
            else:
                st.warning(f"⚠️ No proposals match current active world ({current_active_preview_label}). Filter will be ignored.")
        
        n_steps = st.number_input("Run N predefined proposals", value=default_steps, step=1, min_value=1, max_value=available_proposals, 
                                 help=f"Maximum {available_proposals} proposals are available in selected sequence" + (" (filtered to matching only)" if filter_matching_only else "") + (". Note: Interleaved sequence needs all 8 proposals to reach w4." if proposal_sequence == "All 6 proposals (interleaved)" else ""))
        clear_history = st.checkbox("Clear history before running", value=True, 
                                   help="If checked, resets history and active world to initial state before running the simulation")
        submitted = st.form_submit_button("Run Simulation")

    # Initialize log in session state if not exists
    if "sim_log" not in st.session_state:
        st.session_state.sim_log = []
    
    # Track log updates for refresh
    if "log_update_counter" not in st.session_state:
        st.session_state.log_update_counter = 0
    
    # Display log area
    st.subheader("Simulation Log")
    
    def add_log(message: str, level: str = "INFO"):
        """Add a message to the simulation log"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        st.session_state.sim_log.append(log_entry)
        st.session_state.log_update_counter += 1  # Increment to force refresh
    
    if submitted:
        # Load worlds for name formatting
        _, worlds_dict, _ = load_worlds_and_valuation(examples_dir)
        
        # Clear log at start of simulation
        st.session_state.sim_log = []
        st.session_state.log_update_counter = st.session_state.get("log_update_counter", 0) + 1  # Force refresh
        add_log("=" * 60)
        add_log("Starting new simulation run")
        add_log("=" * 60)
        
        # Clear history if requested
        if clear_history:
            reset_history()
            # Verify history was cleared
            verify_history = read_history()
            if len(verify_history) > 0:
                add_log(f"ERROR: History was not cleared properly. Still has {len(verify_history)} entries.", "ERROR")
            else:
                add_log("History cleared successfully.", "SUCCESS")
            # Verify active world was reset to w1
            verify_active = read_active().get("active_world", "w1")
            if verify_active != "w1":
                verify_active_label = format_world_label(verify_active, worlds_dict)
                add_log(f"ERROR: Active world was not reset to w1. Current value: {verify_active_label}", "ERROR")
            else:
                add_log(f"Active world reset to {format_world_label('w1', worlds_dict)} (default initial state).", "SUCCESS")
        
        rng = random.Random(int(seed))
        voters = build_voters(int(voter_count))
        # Use selected proposal sequence
        if proposal_sequence == "All 6 proposals (interleaved)":
            all_proposals = all_six_proposals_sequence()
        else:
            all_proposals = default_proposals()
        
        # Filter to only matching proposals if requested
        if filter_matching_only:
            current_active = read_active().get("active_world", "w1")
            current_active_label = format_world_label(current_active, worlds_dict)
            matching_proposals = [(pid, src, dst) for pid, src, dst in all_proposals if src == current_active]
            if matching_proposals:
                all_proposals = matching_proposals
                add_log(f"Filtered to {len(matching_proposals)} matching proposal(s) (active world: {current_active_label})")
            else:
                add_log(f"WARNING: No proposals match current active world ({current_active_label}). Running all proposals instead.", "WARNING")
        
        max_available = len(all_proposals)
        requested_steps = int(n_steps)
        
        # Warn if requesting more proposals than available
        if requested_steps > max_available:
            add_log(f"WARNING: Requested {requested_steps} proposals, but only {max_available} are available. Running {max_available} proposals.", "WARNING")
            requested_steps = max_available
        
        proposals = all_proposals[:requested_steps]
        
        # Debug: Show what proposals will be run
        proposal_ids = [p[0] for p in proposals]
        add_log(f"Running {len(proposals)} proposal(s): {proposal_ids}")
        
        last_result = None
        successful_count = 0
        skipped_count = 0
        failed_count = 0
        
        for prop_id, src, dst in proposals:
            # Check current active world before running proposal - read fresh each time
            # Read multiple times to ensure we get the latest data (helps with file system caching)
            current_active_data = read_active()
            current_active = current_active_data.get("active_world", "w1")
            
            # Double-check by reading again
            time.sleep(0.01)  # Slightly longer delay to ensure file system operations complete
            current_active_data2 = read_active()
            current_active2 = current_active_data2.get("active_world", "w1")
            
            if current_active != current_active2:
                # If readings differ, use the second one (more recent)
                current_active = current_active2
                add_log(f"⚠️ Active world reading changed: first read={current_active_data.get('active_world')}, second read={current_active2}", "WARNING")
            
            # Determine proposal direction for display
            is_reverse = "-reverse" in prop_id
            is_forward = "-forward" in prop_id
            direction_label = ""
            if is_reverse:
                direction_label = " [REVERSE - cycle-reversing]"
            elif is_forward:
                direction_label = " [FORWARD - cycle-advancing]"
            
            # Format world labels for display
            src_label = format_world_label(src, worlds_dict)
            dst_label = format_world_label(dst, worlds_dict)
            current_active_label = format_world_label(current_active, worlds_dict)
            
            # Validate that the proposal's from_world matches the current active world FIRST
            if src != current_active:
                add_log(f"SKIPPING {prop_id} ({src_label}→{dst_label}): Current active world is {current_active_label}, but proposal requires {src_label}{direction_label}", "WARNING")
                skipped_count += 1
                continue
            
            # Only log "Processing" for proposals that match and will actually run
            add_log(f"Processing {prop_id}: Current active world = {current_active_label}, Proposal requires = {src_label}{direction_label} ✓ MATCH")
            
            if guaranteed_approval:
                add_log(f"Running {prop_id}: {src_label} → {dst_label}{direction_label} (GUARANTEED APPROVAL MODE - bypassing voting)")
            else:
                add_log(f"Running {prop_id}: {src_label} → {dst_label}{direction_label}")
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
                guaranteed_approval=guaranteed_approval,
            )
            
            if tx is not None:
                successful_count += 1
                # Small delay to ensure file system operations complete
                time.sleep(0.01)
                # Verify active world was updated (read fresh after transition)
                new_active = read_active().get("active_world", "w1")
                new_active_label = format_world_label(new_active, worlds_dict)
                if new_active != dst:
                    add_log(f"ERROR: After {prop_id}, active world is {new_active_label} but should be {dst_label}", "ERROR")
                else:
                    add_log(f"✓ {prop_id} SUCCEEDED: {src_label} → {dst_label}{direction_label} (active world now: {new_active_label})", "SUCCESS")
            else:
                failed_count += 1
                # Provide detailed failure information
                if result:
                    participating_weight = result.votes_for + result.votes_against
                    total_weight = result.total_possible_weight
                    participation_pct = (participating_weight / total_weight * 100) if total_weight > 0 else 0
                    support_pct = (result.votes_for / participating_weight * 100) if participating_weight > 0 else 0
                    threshold_pct = float(threshold) * 100
                    quorum_pct = float(quorum) * 100
                    
                    failure_reasons = []
                    if not result.quorum_met:
                        failure_reasons.append(f"Quorum not met ({participation_pct:.1f}% < {quorum_pct:.1f}%)")
                    if result.quorum_met and support_pct <= threshold_pct:
                        # Note: threshold requires strict majority (support > threshold), so ties fail
                        if support_pct == threshold_pct:
                            failure_reasons.append(f"Threshold not met ({support_pct:.1f}% = {threshold_pct:.1f}% - tie fails, requires >{threshold_pct:.1f}%)")
                        else:
                            failure_reasons.append(f"Threshold not met ({support_pct:.1f}% < {threshold_pct:.1f}%)")
                    
                    reason = " | ".join(failure_reasons) if failure_reasons else "Unknown reason"
                    add_log(f"FAILED {prop_id} ({src_label}→{dst_label}): {reason}", "ERROR")
                    add_log(f"  Votes: FOR={result.votes_for}, AGAINST={result.votes_against}, Total weight={total_weight}, Participating={participating_weight}", "ERROR")
                    add_log(f"  Requirements: Quorum={quorum_pct:.1f}% (met: {result.quorum_met}), Threshold={threshold_pct:.1f}% (support: {support_pct:.1f}%)", "ERROR")
                else:
                    add_log(f"FAILED {prop_id} ({src_label}→{dst_label}): No result returned", "ERROR")
            
            last_result = (prop_id, src, dst, tx, result)
        
        if last_result:
            prop_id, src, dst, tx, result = last_result
            if tx is None:
                add_log(f"Last proposal {prop_id} {src}->{dst} failed. Quorum={result.quorum_met}", "ERROR")
            else:
                add_log(f"Last TX {tx.tx_id}: {src}->{dst} passed.", "SUCCESS")
        
        # Show summary of successful transitions
        final_history = read_history()
        final_active = read_active().get("active_world", "w1")
        summary_parts = [f"{successful_count} succeeded"]
        if failed_count > 0:
            summary_parts.append(f"{failed_count} failed")
        if skipped_count > 0:
            summary_parts.append(f"{skipped_count} skipped (wrong active world)")
        summary = ", ".join(summary_parts)
        
        # Determine which worlds were visited
        visited_worlds = set()
        for h in final_history:
            visited_worlds.add(h.get("from_world"))
            visited_worlds.add(h.get("to_world"))
        visited_worlds_list = sorted(list(visited_worlds))
        visited_worlds_labels = [format_world_label(wid, worlds_dict) for wid in visited_worlds_list]
        final_active_label = format_world_label(final_active, worlds_dict)
        
        add_log("=" * 60)
        add_log(f"Simulation complete: {summary} out of {len(proposals)} proposals.")
        add_log(f"History contains {len(final_history)} transitions. Active world: {final_active_label}")
        add_log(f"Visited worlds: {', '.join(visited_worlds_labels) if visited_worlds_labels else 'None'}")
        if proposal_sequence == "All 6 proposals (interleaved)" and "w4" not in visited_worlds:
            add_log("⚠️ WARNING: w4 was not visited. The interleaved sequence requires all 8 proposals to reach w4. Did you run all 8 proposals?", "WARNING")
        add_log("=" * 60)
        
        st.session_state.refresh_counter = st.session_state.get("refresh_counter", 0) + 1
        st.rerun()
    
    # Display current log - always show, even if empty (to show it was cleared)
    log_text = "\n".join(st.session_state.sim_log) if st.session_state.sim_log else "(Log cleared - ready for new simulation)"
    # Use dynamic key based on update counter to force refresh
    log_key = f"log_display_{st.session_state.get('log_update_counter', 0)}_{len(st.session_state.sim_log)}"
    st.text_area("", value=log_text, height=300, disabled=True, key=log_key, label_visibility="collapsed")

    st.divider()
    st.subheader("Run Custom Proposal")
    
    # Initialize custom proposal log in session state
    if "custom_proposal_log" not in st.session_state:
        st.session_state.custom_proposal_log = []
    if "custom_log_update_counter" not in st.session_state:
        st.session_state.custom_log_update_counter = 0
    
    def add_custom_log(message: str, level: str = "INFO"):
        """Add a message to the custom proposal log"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        st.session_state.custom_proposal_log.append(log_entry)
        st.session_state.custom_log_update_counter += 1
    
    store, worlds, model = load_worlds_and_valuation(examples_dir)
    world_ids = sorted(worlds.keys())
    # Create labels with world names for selectboxes
    from_world_options = {format_world_label(wid, worlds): wid for wid in world_ids}
    to_world_options = {format_world_label(wid, worlds): wid for wid in world_ids}
    c1, c2, c3 = st.columns(3)
    from_w_label = c1.selectbox("From world", list(from_world_options.keys()), index=0)
    from_w = from_world_options[from_w_label]
    # Filter out the selected "from" world from "to" options
    to_world_options_filtered = {k: v for k, v in to_world_options.items() if v != from_w}
    to_w_label = c2.selectbox("To world", list(to_world_options_filtered.keys()), index=0)
    to_w = to_world_options_filtered[to_w_label]
    prop_id_custom = c3.text_input("Proposal ID", value="prop-custom")
    
    # Note: guaranteed_approval from form is available in this scope
    if st.button("Run Proposal"):
        # Clear log at start
        st.session_state.custom_proposal_log = []
        st.session_state.custom_log_update_counter += 1
        
        add_custom_log("=" * 60)
        add_custom_log("Starting custom proposal")
        add_custom_log("=" * 60)
        
        # Check current active world
        current_active = read_active().get("active_world", "w1")
        current_active_label = format_world_label(current_active, worlds)
        from_w_label_display = format_world_label(from_w, worlds)
        to_w_label_display = format_world_label(to_w, worlds)
        
        add_custom_log(f"Proposal: {prop_id_custom}")
        add_custom_log(f"Transition: {from_w_label_display} → {to_w_label_display}")
        add_custom_log(f"Current active world: {current_active_label}")
        
        # Check if proposal matches active world
        if from_w != current_active:
            add_custom_log(f"⚠️ WARNING: Current active world ({current_active_label}) does not match proposal source ({from_w_label_display}). Proposal may fail or be skipped.", "WARNING")
        else:
            add_custom_log(f"✓ Active world matches proposal source ({from_w_label_display})", "SUCCESS")
        
        if guaranteed_approval:
            add_custom_log("Mode: GUARANTEED APPROVAL (bypassing voting)")
        else:
            add_custom_log(f"Parameters: Quorum={quorum:.1%}, Threshold={threshold:.1%}, Approval prob={approval_prob:.1%}, Participation prob={participation_prob:.1%}")
        
        rng = random.Random(int(seed))
        voters = build_voters(int(voter_count))
        total_weight = sum(v.weight for v in voters.values())
        add_custom_log(f"Voters: {len(voters)} (total weight: {total_weight})")
        
        add_custom_log("Running proposal...")
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
            guaranteed_approval=guaranteed_approval,
        )
        
        if tx is None:
            # Proposal failed
            if result:
                participating_weight = result.votes_for + result.votes_against
                participation_pct = (participating_weight / total_weight * 100) if total_weight > 0 else 0
                support_pct = (result.votes_for / participating_weight * 100) if participating_weight > 0 else 0
                threshold_pct = float(threshold) * 100
                quorum_pct = float(quorum) * 100
                
                failure_reasons = []
                if not result.quorum_met:
                    failure_reasons.append(f"Quorum not met ({participation_pct:.1f}% < {quorum_pct:.1f}%)")
                if result.quorum_met and support_pct <= threshold_pct:
                    if support_pct == threshold_pct:
                        failure_reasons.append(f"Threshold not met ({support_pct:.1f}% = {threshold_pct:.1f}% - tie fails, requires >{threshold_pct:.1f}%)")
                    else:
                        failure_reasons.append(f"Threshold not met ({support_pct:.1f}% < {threshold_pct:.1f}%)")
                
                reason = " | ".join(failure_reasons) if failure_reasons else "Unknown reason"
                add_custom_log(f"❌ FAILED: {reason}", "ERROR")
                add_custom_log(f"  Votes: FOR={result.votes_for}, AGAINST={result.votes_against}, Total weight={total_weight}, Participating={participating_weight}", "ERROR")
                add_custom_log(f"  Requirements: Quorum={quorum_pct:.1f}% (met: {result.quorum_met}), Threshold={threshold_pct:.1f}% (support: {support_pct:.1f}%)", "ERROR")
            else:
                add_custom_log("❌ FAILED: No result returned", "ERROR")
            add_custom_log("=" * 60)
            st.warning(f"Proposal failed. Quorum={result.quorum_met if result else 'unknown'}")
        else:
            # Proposal succeeded
            new_active = read_active().get("active_world", "w1")
            new_active_label = format_world_label(new_active, worlds)
            
            add_custom_log(f"✅ SUCCEEDED: {from_w_label_display} → {to_w_label_display}", "SUCCESS")
            if result:
                participating_weight = result.votes_for + result.votes_against
                add_custom_log(f"  Votes: FOR={result.votes_for}, AGAINST={result.votes_against}, Participating={participating_weight}")
                add_custom_log(f"  Transaction ID: {tx.tx_id}")
            add_custom_log(f"  Active world updated to: {new_active_label}")
            add_custom_log("=" * 60)
            st.success(f"TX {tx.tx_id}: {from_w_label_display} → {to_w_label_display} passed.")
        
        st.session_state.refresh_counter = st.session_state.get("refresh_counter", 0) + 1
        st.rerun()
    
    # Display custom proposal log
    st.subheader("Custom Proposal Log")
    if st.session_state.custom_proposal_log:
        log_text = "\n".join(st.session_state.custom_proposal_log)
        log_key = f"custom_log_display_{st.session_state.custom_log_update_counter}_{len(st.session_state.custom_proposal_log)}"
        st.text_area("", value=log_text, height=300, disabled=True, key=log_key, label_visibility="collapsed")
    else:
        st.info("(Log will appear here after running a custom proposal)")


with tab_graph:
    st.markdown(
        """
        View the Kripke model as a directed graph. The active world is highlighted in yellow.
        """
    )
    with st.expander("ℹ️ What is a Kripke Model?"):
        st.markdown(
            """
            **Kripke Model**: A mathematical structure used to represent possible worlds and their relationships.
            
            - **Worlds (nodes)**: Each circle represents a possible governance state (e.g., w1 = Base Governance, w2 = Quorum Enabled)
            - **Edges (arrows)**: Show which transitions are allowed (the **Accessibility Relation**). An arrow from w1 to w2 means you can transition from w1 to w2, but not necessarily the reverse.
            - **Valuation**: Each world has a truth assignment showing which propositions (p1, p2, p3, p4) are true in that world, displayed as {p1, p2, ...}
            
            The model provides a formal way to reason about what governance states are possible, which transitions are valid, and what properties hold in different configurations.
            """
        )
    with st.expander("Graph elements"):
        st.markdown(
            """
            - **Nodes (circles)**: Worlds (w1, w2, w3, w4) with their truth assignments shown as {p1, p2, ...}.
            - **Edges (arrows)**: Possible transitions between worlds.
            - **Yellow node**: The currently active world.
            - **Green nodes**: Worlds that have been visited by successful proposals (but not currently active).
            - **Blue nodes**: Worlds that have not yet been visited.
            - **Layout**: Spring layout (may vary on refresh).
            """
        )
    # Force refresh by including refresh counter and active world in computation
    refresh_counter = st.session_state.get("refresh_counter", 0)
    active = read_active()
    active_world = active.get("active_world", "w1")
    last_tx = active.get("last_tx", "")
    # Include active world state to force regeneration
    _ = (refresh_counter, active_world, last_tx)
    
    store, worlds, model = load_worlds_and_valuation(examples_dir)
    props = sorted(list(model.valuation.keys()))
    # Create labels with world names: "w1 (Base Governance):{p1}"
    labels = {}
    for w_id in worlds:
        world = worlds[w_id]
        world_name = world.name
        # Get the proposition summary from the model
        prop_summary = model.summarize_world_label(w_id, props)
        # Extract just the proposition part (after the colon)
        if ":" in prop_summary:
            prop_part = prop_summary.split(":", 1)[1]
            labels[w_id] = f"{w_id} ({world_name}):{prop_part}"
        else:
            labels[w_id] = f"{w_id} ({world_name})"
    history_path = os.path.join(examples_dir, "history.json")
    st.image(graph_png_bytes(store.G, active_world, labels, history_path))
    
    # Add legend explaining node colors
    st.markdown("**Node Colors:**")
    col1, col2, col3 = st.columns(3)
    col1.markdown("🟡 **Yellow**: Active world (current state)")
    col2.markdown("🟢 **Green**: Visited world (has been reached by a successful proposal)")
    col3.markdown("🔵 **Blue**: Unvisited world (not yet reached)")


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
    
    # Create comprehensive signature that changes with any history change
    # Include actual history content hash to ensure uniqueness
    history_content_hash = hash(str(history)) if history else 0
    history_signature = f"{history_count}_{refresh_counter}_{file_mtime}_{history_content_hash}"
    
    # Also check active world to ensure we refresh when it changes
    active = read_active()
    active_world = active.get("active_world", "w1")
    history_signature += f"_{active_world}"
    
    # Force Streamlit to recognize this as a new computation by using signature
    timeline_key = f"timeline_{history_signature}"
    _ = timeline_key
    
    # Always read from file and regenerate timeline
    tl_bytes = timeline_png_bytes(history_path)
    
    # Use empty container to force refresh
    timeline_container = st.empty()
    if tl_bytes:
        # Display image - Streamlit should regenerate due to signature change
        timeline_container.image(tl_bytes, width='stretch')
    else:
        timeline_container.info("No timeline yet. Run a simulation to generate transitions.")
    
    # Display dataframe with unique key
    data = history
    if data:
        st.dataframe(data, width='stretch', hide_index=True, key=f"timeline_df_{history_signature}")


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
    # Force refresh by including refresh counter and file modification times
    refresh_counter = st.session_state.get("refresh_counter", 0)
    history = read_history()
    history_count = len(history)
    
    # Get file modification times to detect changes
    history_path = os.path.join(examples_dir, "history.json")
    active_path = os.path.join(examples_dir, "active_world.json")
    history_mtime = os.path.getmtime(history_path) if os.path.exists(history_path) else 0
    active_mtime = os.path.getmtime(active_path) if os.path.exists(active_path) else 0
    
    # Create signature with history content hash to force refresh
    history_content_hash = hash(str(history)) if history else 0
    data_signature = f"{refresh_counter}_{history_count}_{history_mtime}_{active_mtime}_{history_content_hash}"
    _ = data_signature
    
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
    # Always read fresh from file - force refresh by including in computation
    current_history = read_history()
    # Include history content in signature to force refresh
    history_json_key = f"history_json_{data_signature}_{hash(str(current_history))}"
    _ = history_json_key
    # Use container to force refresh
    history_container = st.empty()
    history_container.json(current_history)
    
    # Truth table for valuation.json
    st.subheader("Truth Table")
    st.markdown("Tabular representation of **valuation.json**: Shows which propositions are true in each world.")
    val_path = os.path.join(examples_dir, "valuation.json")
    if os.path.exists(val_path):
        # Load valuation
        with open(val_path, 'r', encoding='utf-8') as f:
            valuation = json.load(f)
        
        # Get all worlds from the graph store
        store, worlds, model = load_worlds_and_valuation(examples_dir)
        world_ids = sorted(worlds.keys())
        
        # Get all propositions (sorted)
        propositions = sorted(valuation.keys())
        
        # Build truth table data with world names
        truth_table_data = []
        for world_id in world_ids:
            world_label = format_world_label(world_id, worlds)
            row = {"World": world_label}
            for prop in propositions:
                # Check if this proposition is true in this world
                is_true = world_id in valuation.get(prop, [])
                row[prop] = "✓" if is_true else "✗"
            truth_table_data.append(row)
        
        # Display as dataframe (Streamlit can handle list of dicts directly)
        st.dataframe(truth_table_data, width='stretch', use_container_width=True, hide_index=False)
        
        # Add explanation
        with st.expander("Truth table explained"):
            st.markdown(
                """
                - **Rows**: Each world (w1, w2, w3, w4)
                - **Columns**: Each proposition (p1, p2, p3, p4)
                - **✓**: Proposition is true in this world
                - **✗**: Proposition is false in this world
                
                This table shows the valuation function V: Prop → P(W), where each proposition 
                maps to the set of worlds where it is true.
                """
            )
    else:
        st.info("No valuation.json yet. Initialize the graph to generate the truth table.")


