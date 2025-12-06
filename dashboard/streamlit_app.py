from __future__ import annotations

import io
import json
import os
import random
import sys
import time
from typing import Dict

import streamlit as st

try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

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


root = ROOT
examples_dir, worlds_dir = ensure_examples_dirs(root)

# Logo configuration - QA DAO logo
# Logo file should be saved as "logo.jpg" in the dashboard directory
LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo.jpg")

# Set page config with logo as favicon if available
page_icon_path = LOGO_PATH if os.path.exists(LOGO_PATH) else "🔮"
st.set_page_config(
    page_title="PWSGT Dashboard", 
    layout="wide",
    page_icon=page_icon_path
)

# Display logo next to title in header
if LOGO_PATH and os.path.exists(LOGO_PATH):
    col_logo, col_title = st.columns([1, 10])
    with col_logo:
        st.image(LOGO_PATH, width=80)  # Smaller size to fit next to title
    with col_title:
        st.title("PWSGT – Cyclic Possible World Governance (Simulation)")
elif LOGO_PATH:
    st.sidebar.warning(f"Logo not found at: {LOGO_PATH}")
    st.title("PWSGT – Cyclic Possible World Governance (Simulation)")
else:
    st.title("PWSGT – Cyclic Possible World Governance (Simulation)")


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


tab_overview, tab_run, tab_graph, tab_timeline, tab_data, tab_modal, tab_about = st.tabs([
    "System Status & Setup", "Simulation & Control", "Kripke Model Explorer", "Governance History", "Raw Data Dump", "Modal Logic Explorer", "About CPWS",
])


with tab_about:
    st.header("About Cyclic Possible World Semantics (CPWS)")
    
    # High-Level Overview
    st.markdown(
        """
        CPWS combines modal logic with governance to create a resilient, non-linear DAO roadmap. It defines possible future states and the rules for moving between them.
        """
    )
    
    st.divider()
    
    # Concept 1: World (The Governance Snapshot)
    st.markdown("### 🌍 World (The Governance Snapshot)")
    st.markdown("A defined state or snapshot of the protocol's current parameters.")
    st.markdown(
        """
        Each world (e.g., W1, W2) holds a set of propositions (p₁, p₂, etc.) that are either true or false. In governance, this means specific features are ON or OFF, or certain parameters are set to specific values.
        """
    )
    
    st.divider()
    
    # Concept 2: Accessibility Relation (The Roadmap)
    st.markdown("### 🗺️ Accessibility Relation (The Roadmap)")
    st.markdown("The \"Rulebook\" that defines which state can legally follow another.")
    st.markdown(
        """
        This is represented by the graph's edges (e.g., W1 → W2). A transition is only possible if an edge exists, meaning the governance has a predefined path to move between those two states. If no edge exists, that move is logically blocked.
        """
    )
    
    st.divider()
    
    # Concept 3: Cyclic Nature (The Continuous Loop)
    st.markdown("### 🔄 Cyclic Nature (The Continuous Loop)")
    st.markdown("The system can revisit or correct past states, preventing permanent \"dead ends.\"")
    st.markdown(
        """
        The graph includes a full cycle (like W4 → W1) and reverse transitions (like W2 → W1). This is crucial for governance, as it means the community can always vote to revert an unsuccessful change, ensuring resilience and adaptability.
        """
    )


with tab_overview:
    # Load data for Current State Summary and Quick Actions
    active = read_active()
    history = read_history()
    # Load worlds to get names for display
    try:
        _, worlds_dict, _ = load_worlds_and_valuation(examples_dir)
        active_world_id = active.get("active_world", "w1")
        active_world_label = format_world_label(active_world_id, worlds_dict)
    except Exception:
        worlds_dict = {}
        active_world_id = active.get("active_world", "w1")
        active_world_label = active.get("active_world", "w1")
    
    transition_count = len(history)
    
    # Show current state summary
    st.subheader("📋 Current State Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Active World**")
        st.markdown(f'<p style="font-size: 24px; font-weight: bold;">{active_world_label}</p>', unsafe_allow_html=True)
    
    with col2:
        st.markdown("**Total Transitions**")
        st.markdown(f'<p style="font-size: 24px; font-weight: bold;">{transition_count}</p>', unsafe_allow_html=True)
    
    with col3:
        st.markdown("**Last Transition**")
        if transition_count > 0:
            last_transition = history[-1]
            from_world = last_transition.get("from_world", "?")
            to_world = last_transition.get("to_world", "?")
            try:
                from_label = format_world_label(from_world, worlds_dict)
                to_label = format_world_label(to_world, worlds_dict)
            except:
                from_label = from_world
                to_label = to_world
            st.markdown(f'<p style="font-size: 24px; font-weight: bold;">{from_label} → {to_label}</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p style="font-size: 24px; font-weight: bold;">None yet</p>', unsafe_allow_html=True)
    
    st.divider()
    
    # Quick actions
    st.subheader("🚀 Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Initialize Example Graph", use_container_width=True):
            init_graph_script()
            st.success("Initialized worlds and graph in examples/.")
            st.session_state.refresh_counter = st.session_state.get("refresh_counter", 0) + 1
            st.rerun()
    
    with col2:
        if st.button("🗑️ Reset History", use_container_width=True):
            reset_history()
            # Verify reset worked - active world should always be w1 after reset
            verify_active = read_active().get("active_world", "w1")
            verify_history = read_history()
            if verify_active == "w1" and len(verify_history) == 0:
                st.success(f"Cleared history and reset active world to w1 (default initial state).")
            else:
                st.error(f"Reset may have failed. Active world: {verify_active} (expected w1), History entries: {len(verify_history)}")
            st.session_state.refresh_counter = st.session_state.get("refresh_counter", 0) + 1
            st.rerun()
    
    with col3:
        st.markdown("**Next Steps:**\n\n1. Go to **Simulation & Control** to run a simulation\n2. Check **Kripke Model Explorer** tab to see the visual representation\n3. View **Governance History** to see transition history")
    
    st.divider()
    
    # Dashboard Overview header moved here
    st.header("📊 Dashboard Overview")
    
    st.markdown(
        """
        Welcome! This is your **guided tour** of the governance simulation dashboard. 
        Let's start by understanding the two most important concepts: the **Active World** and **Transition Count**.
        """
    )
    
    st.divider()
    
    # Section 1: Active World
    st.subheader("📍 Step 1: Understanding the Active World")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        **What is the Active World?**
        
        The **Active World** is the current governance state that is in effect right now. 
        Think of it as the "current version" of your DAO's governance rules.
        
        **How it works:**
        - When the simulation starts, the active world is **w1 (Base Governance)** by default
        - When a governance proposal **passes** (meets quorum and threshold), the active world changes to the proposal's destination
        - When a proposal **fails**, the active world stays the same
        
        **Why it matters:**
        - Only proposals that match the active world can run (e.g., if active world is w2, only proposals starting from w2 can execute)
        - The active world determines which governance rules are currently in effect
        - You can see the active world highlighted in **yellow** in the Kripke Model Explorer tab
        """)
    
    with col2:
        st.metric("🎯 Active World", active_world_label)
        
        # Show explanation based on active world
        if active_world_id == "w1":
            st.info("**Base Governance** - The starting state with minimal rules.")
        elif active_world_id == "w2":
            st.info("**Quorum Enabled** - Quorum requirements are now active.")
        elif active_world_id == "w3":
            st.info("**Delegated Governance** - Delegation features are enabled.")
        elif active_world_id == "w4":
            st.info("**Council Governance** - Council-based governance is active.")
    
    st.divider()
    
    # Section 2: Transition Count
    st.subheader("🔄 Step 2: Understanding Transition Count")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        **What is a Transition?**
        
        A **transition** is a successful governance proposal that moved the system from one world to another.
        Each time a proposal passes (meets quorum and threshold), it creates a transition.
        
        **How transitions work:**
        1. A proposal attempts to move from World A → World B
        2. Voters participate and vote "for" or "against"
        3. If the proposal **passes** (quorum + threshold met), a transition occurs:
           - The active world changes from A to B
           - A transition record is added to the history
           - The transition count increases by 1
        4. If the proposal **fails**, no transition occurs (active world stays the same)
        
        **Why it matters:**
        - Transition count shows how many successful governance changes have occurred
        - Each transition represents a community decision that changed the governance state
        - You can see all transitions in the **Governance History** tab
        - The history of transitions shows the governance journey over time
        """)
    
    with col2:
        st.metric("📈 Total Transitions", transition_count)
        
        if transition_count == 0:
            st.info("**No transitions yet.** Run a simulation in the **Simulation & Control** tab to create transitions!")
        elif transition_count == 1:
            st.success(f"**1 transition** recorded. Check the Governance History tab to see it!")
        else:
            st.success(f"**{transition_count} transitions** recorded. The system has evolved through {transition_count} governance changes!")
    
    st.divider()
    
    # Section 3: Putting it Together
    st.subheader("🔗 Step 3: How Active World and Transitions Work Together")
    
    st.markdown("""
    **The Relationship:**
    
    - **Active World** = Where you are now
    - **Transitions** = How you got here (the journey)
    
    **Example Journey:**
    
    1. **Start**: Active World = w1 (Base Governance), Transitions = 0
    2. **Proposal 1 passes** (w1 → w2): 
       - ✅ Transition created (Transitions = 1)
       - ✅ Active World changes to w2 (Quorum Enabled)
    3. **Proposal 2 passes** (w2 → w3):
       - ✅ Transition created (Transitions = 2)
       - ✅ Active World changes to w3 (Delegated Governance)
    4. **Proposal 3 fails** (w3 → w4):
       - ❌ No transition created (Transitions still = 2)
       - ❌ Active World stays at w3 (no change)
    5. **Proposal 4 passes** (w3 → w2):
       - ✅ Transition created (Transitions = 3)
       - ✅ Active World changes to w2 (back to Quorum Enabled)
    
    Notice how the system can go **backwards** (w3 → w2) - this is the **cyclic** nature of possible worlds!
    """)
    
    st.divider()
    
    # Additional help
    with st.expander("💡 Need More Help?"):
        st.markdown("""
        - **About CPWS Tab**: Learn about the core concepts and real-world utility
        - **System Status & Setup Tab**: View current state and initialize the system
        - **Simulation & Control Tab**: Set parameters and run simulations
        - **Kripke Model Explorer Tab**: Visualize the Kripke model and see which worlds have been visited
        - **Governance History Tab**: View the sequence of transitions over time
        - **Raw Data Dump Tab**: Inspect raw JSON files and truth tables
        """)


with tab_run:
    st.markdown(
        """
        **Central experimentation area** for governance simulations. Follow the 3-step workflow below to configure and run proposals.
        """
    )
    
    # Initialize session state for failure notifications
    if "proposal_failures" not in st.session_state:
        st.session_state.proposal_failures = []
    if "proposal_successes" not in st.session_state:
        st.session_state.proposal_successes = []
    
    # ============================================
    # SIDEBAR: Core Voting Parameters
    # ============================================
    with st.sidebar:
        st.header("⚙️ Core Voting Parameters")
        st.markdown("Configure the essential voting parameters that control proposal outcomes.")
        
        with st.expander("ℹ️ Parameter Guide"):
            st.markdown(
                """
                **Quorum**: Minimum % of total voting weight that must participate (e.g., 0.5 = 50%).
                
                **Approval Threshold**: Minimum % of participating votes that must be "for" to pass. Requires **strict majority** (support > threshold), so ties fail.
                
                **Voter Approval Probability**: Chance each voter votes "for" (0.6 = 60%). Higher = more likely to pass.
                
                **Participation Probability**: Chance each voter participates (0.95 = 95%). Lower = harder to meet quorum.
                
                **Voters**: Number of simulated voters with weights 1, 2, 3, ..., N.
                
                **Seed**: Random seed for reproducible simulations.
                """
            )
        
        # Core parameters in sidebar
        quorum = st.slider(
            "Quorum", 
            0.0, 1.0, 0.5, 0.05,
            help="Minimum percentage of total voting weight that must participate (0.0-1.0). Example: 0.5 = 50%",
            key="sidebar_quorum"
        )
        st.caption(f"Current: {quorum:.0%}")
        
        threshold = st.slider(
            "Approval Threshold", 
            0.0, 1.0, 0.5, 0.05,
            help="Minimum percentage of participating votes that must be 'for' to pass. Requires strict majority (support > threshold).",
            key="sidebar_threshold"
        )
        st.caption(f"Current: {threshold:.0%}")
        
        approval_prob = st.slider(
            "Voter Approval Probability", 
            0.0, 1.0, 0.6, 0.05,
            help="Probability each voter votes 'for' (0.0-1.0). Higher values increase pass rate.",
            key="sidebar_approval_prob"
        )
        st.caption(f"Current: {approval_prob:.0%}")
        
        st.divider()
        
        participation_prob = st.slider(
            "Participation Probability", 
            0.0, 1.0, 0.95, 0.05,
            help="Probability each voter participates (0.0-1.0). Lower values make quorum harder to meet.",
            key="sidebar_participation_prob"
        )
        st.caption(f"Current: {participation_prob:.0%}")
        
        voter_count = st.number_input(
            "Number of Voters", 
            value=10, step=1, min_value=1, max_value=100,
            help="Number of simulated voters. Each has weight 1, 2, 3, ..., N.",
            key="sidebar_voter_count"
        )
        
        seed = st.number_input(
            "Random Seed", 
            value=42, step=1,
            help="Random number generator seed for reproducible simulations.",
            key="sidebar_seed"
        )
        
        st.divider()
        
        guaranteed_approval = st.checkbox(
            "Guaranteed Approval Mode", 
            value=False,
            help="If enabled, all matching proposals automatically pass (bypasses voting). Useful for testing transitions.",
            key="sidebar_guaranteed"
        )
    
    # ============================================
    # MAIN AREA: 3-Step Workflow
    # ============================================
    
    # Step 1: Set Parameters (already in sidebar, show summary)
    st.header("📋 Step 1: Set Parameters")
    col_param1, col_param2, col_param3 = st.columns(3)
    with col_param1:
        st.metric("Quorum", f"{quorum:.0%}")
    with col_param2:
        st.metric("Approval Threshold", f"{threshold:.0%}")
    with col_param3:
        st.metric("Voter Approval Probability", f"{approval_prob:.0%}")
    st.info("💡 Adjust parameters in the **sidebar** on the left. Sliders use 5% increments (0.05 steps).")
    
    st.divider()
    
    # Step 2: Choose Proposals
    st.header("📝 Step 2: Choose Proposals")
    
    with st.expander("ℹ️ Understanding Proposals"):
        st.markdown(
            """
            **Proposal Types:**
            - **Forward proposals** (prop-001 through prop-004): Advance through the cycle w1→w2→w3→w4→w1
            - **Reverse proposals** (prop-005, prop-006): Reverse the cycle (w2→w1, w3→w2), demonstrating cyclic nature
            
            **Proposal Execution:**
            - Proposals run **sequentially** in order
            - Each proposal checks if the **current active world** matches its `from_world`
            - If matched, the proposal runs a vote simulation
            - If **passes** (quorum + threshold met), active world transitions to `to_world`
            - If **fails**, active world stays unchanged and subsequent mismatched proposals are skipped
            """
        )
    
    with st.form("run_form"):
        proposal_sequence = st.radio(
            "Proposal Sequence",
            ["Default (forward cycle + reverse)", "All 6 proposals (interleaved)"],
            help="Default: 4 forward proposals complete the cycle. All 6: interleaved sequence with reverse transitions (requires 8 proposals to reach w4).",
            horizontal=True
        )
        
        # Get the actual number of available proposals based on selected sequence
        if proposal_sequence == "All 6 proposals (interleaved)":
            all_proposals_list = all_six_proposals_sequence()
            default_steps = 8  # Need all 8 to reach w4
            st.info("ℹ️ **Interleaved sequence**: 8 proposals total. Run all 8 to reach w4.")
        else:
            all_proposals_list = default_proposals()
            default_steps = 6
        available_proposals = len(all_proposals_list)
        
        filter_matching_only = st.checkbox(
            "Show only matching proposals", 
            value=False,
            help="If enabled, only proposals that match the current active world will be included."
        )
        
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
        
        col_step2_1, col_step2_2 = st.columns(2)
        with col_step2_1:
            n_steps = st.number_input(
                "Run N Predefined Proposals", 
                value=default_steps, step=1, min_value=1, max_value=available_proposals, 
                help=f"Maximum {available_proposals} proposals available" + (" (filtered to matching only)" if filter_matching_only else "") + ("." if proposal_sequence != "All 6 proposals (interleaved)" else ". Note: Interleaved sequence needs all 8 proposals to reach w4.")
            )
        with col_step2_2:
            clear_history = st.checkbox(
                "Clear history before running", 
                value=True, 
                help="If checked, resets history and active world to initial state (w1) before running."
            )
        
        st.divider()
        
        # Step 3: Run Simulation
        st.header("🚀 Step 3: Run Simulation")
        submitted = st.form_submit_button("▶️ Run Simulation", type="primary", use_container_width=True)

    # Initialize log in session state if not exists
    if "sim_log" not in st.session_state:
        st.session_state.sim_log = []
    
    # Track log updates for refresh
    if "log_update_counter" not in st.session_state:
        st.session_state.log_update_counter = 0
    
    # Initialize notification storage
    if "proposal_failures" not in st.session_state:
        st.session_state.proposal_failures = []
    if "proposal_successes" not in st.session_state:
        st.session_state.proposal_successes = []
    
    # Real-time Feedback Area (above log) - only show if there are notifications
    if st.session_state.proposal_failures or st.session_state.proposal_successes:
        st.divider()
        st.subheader("📊 Real-time Feedback")
        
        # Display failure notifications
        if st.session_state.proposal_failures:
            for failure in st.session_state.proposal_failures:
                st.error(f"❌ **Proposal Failed**: {failure}")
        
        # Display success notifications (last 3)
        if st.session_state.proposal_successes:
            for success in st.session_state.proposal_successes[-3:]:
                st.success(f"✅ **Proposal Passed**: {success}")
    
    # Display log area
    st.subheader("📋 Simulation Log")
    
    def add_log(message: str, level: str = "INFO"):
        """Add a message to the simulation log"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        st.session_state.sim_log.append(log_entry)
        st.session_state.log_update_counter += 1  # Increment to force refresh

    if submitted:
        # Clear previous notifications
        st.session_state.proposal_failures = []
        st.session_state.proposal_successes = []
        st.session_state.simulation_started = True
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
                    success_msg = f"{prop_id} ({src_label} → {dst_label})"
                    add_log(f"✓ {prop_id} SUCCEEDED: {src_label} → {dst_label}{direction_label} (active world now: {new_active_label})", "SUCCESS")
                    # Store success for notification
                    if result:
                        participating_weight = result.votes_for + result.votes_against
                        support_pct = (result.votes_for / participating_weight * 100) if participating_weight > 0 else 0
                        st.session_state.proposal_successes.append(f"{success_msg} - {support_pct:.1f}% support")
                    else:
                        st.session_state.proposal_successes.append(success_msg)
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
                    failure_msg_parts = []
                    
                    if not result.quorum_met:
                        failure_reasons.append(f"Quorum not met ({participation_pct:.1f}% < {quorum_pct:.1f}%)")
                        failure_msg_parts.append(f"Quorum not met ({participation_pct:.1f}% participation when {quorum_pct:.1f}% was required)")
                    
                    if result.quorum_met and support_pct <= threshold_pct:
                        # Note: threshold requires strict majority (support > threshold), so ties fail
                        if support_pct == threshold_pct:
                            failure_reasons.append(f"Threshold not met ({support_pct:.1f}% = {threshold_pct:.1f}% - tie fails, requires >{threshold_pct:.1f}%)")
                            failure_msg_parts.append(f"Threshold not met ({support_pct:.1f}% support when {threshold_pct:.1f}% was required - tie fails)")
                        else:
                            failure_reasons.append(f"Threshold not met ({support_pct:.1f}% < {threshold_pct:.1f}%)")
                            failure_msg_parts.append(f"Threshold not met ({support_pct:.1f}% support when {threshold_pct:.1f}% was required)")
                    
                    reason = " | ".join(failure_reasons) if failure_reasons else "Unknown reason"
                    failure_notification = f"{prop_id} ({src_label} → {dst_label}): {' | '.join(failure_msg_parts) if failure_msg_parts else reason}"
                    
                    # Add to log
                    add_log(f"FAILED {prop_id} ({src_label}→{dst_label}): {reason}", "ERROR")
                    add_log(f"  Votes: FOR={result.votes_for}, AGAINST={result.votes_against}, Total weight={total_weight}, Participating={participating_weight}", "ERROR")
                    add_log(f"  Requirements: Quorum={quorum_pct:.1f}% (met: {result.quorum_met}), Threshold={threshold_pct:.1f}% (support: {support_pct:.1f}%)", "ERROR")
                    
                    # Store failure for notification (will be displayed above log)
                    st.session_state.proposal_failures.append(failure_notification)
                else:
                    failure_notification = f"{prop_id} ({src_label} → {dst_label}): No result returned"
                    add_log(f"FAILED {prop_id} ({src_label}→{dst_label}): No result returned", "ERROR")
                    st.session_state.proposal_failures.append(failure_notification)
            
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
                failure_msg_parts = []
                
                if not result.quorum_met:
                    failure_reasons.append(f"Quorum not met ({participation_pct:.1f}% < {quorum_pct:.1f}%)")
                    failure_msg_parts.append(f"Quorum not met ({participation_pct:.1f}% participation when {quorum_pct:.1f}% was required)")
                
                if result.quorum_met and support_pct <= threshold_pct:
                    if support_pct == threshold_pct:
                        failure_reasons.append(f"Threshold not met ({support_pct:.1f}% = {threshold_pct:.1f}% - tie fails, requires >{threshold_pct:.1f}%)")
                        failure_msg_parts.append(f"Threshold not met ({support_pct:.1f}% support when {threshold_pct:.1f}% was required - tie fails)")
                    else:
                        failure_reasons.append(f"Threshold not met ({support_pct:.1f}% < {threshold_pct:.1f}%)")
                        failure_msg_parts.append(f"Threshold not met ({support_pct:.1f}% support when {threshold_pct:.1f}% was required)")
                
                reason = " | ".join(failure_reasons) if failure_reasons else "Unknown reason"
                failure_notification = f"{prop_id_custom} ({from_w_label_display} → {to_w_label_display}): {' | '.join(failure_msg_parts) if failure_msg_parts else reason}"
                
                add_custom_log(f"❌ FAILED: {reason}", "ERROR")
                add_custom_log(f"  Votes: FOR={result.votes_for}, AGAINST={result.votes_against}, Total weight={total_weight}, Participating={participating_weight}", "ERROR")
                add_custom_log(f"  Requirements: Quorum={quorum_pct:.1f}% (met: {result.quorum_met}), Threshold={threshold_pct:.1f}% (support: {support_pct:.1f}%)", "ERROR")
                
                # Store failure for notification
                st.session_state.proposal_failures.append(failure_notification)
                # Also show immediate error notification
                st.error(f"❌ **Proposal Failed**: {failure_notification}")
            else:
                failure_notification = f"{prop_id_custom} ({from_w_label_display} → {to_w_label_display}): No result returned"
                add_custom_log("❌ FAILED: No result returned", "ERROR")
                st.session_state.proposal_failures.append(failure_notification)
                st.error(f"❌ **Proposal Failed**: {failure_notification}")
            add_custom_log("=" * 60)
        else:
            # Proposal succeeded
            new_active = read_active().get("active_world", "w1")
            new_active_label = format_world_label(new_active, worlds)
            
            add_custom_log(f"✅ SUCCEEDED: {from_w_label_display} → {to_w_label_display}", "SUCCESS")
            if result:
                participating_weight = result.votes_for + result.votes_against
                support_pct = (result.votes_for / participating_weight * 100) if participating_weight > 0 else 0
                add_custom_log(f"  Votes: FOR={result.votes_for}, AGAINST={result.votes_against}, Participating={participating_weight}")
                add_custom_log(f"  Transaction ID: {tx.tx_id}")
                
                # Store success for notification
                success_msg = f"{prop_id_custom} ({from_w_label_display} → {to_w_label_display}) - {support_pct:.1f}% support"
                st.session_state.proposal_successes.append(success_msg)
            else:
                success_msg = f"{prop_id_custom} ({from_w_label_display} → {to_w_label_display})"
                st.session_state.proposal_successes.append(success_msg)
            
            add_custom_log(f"  Active world updated to: {new_active_label}")
            add_custom_log("=" * 60)
            st.success(f"✅ **Proposal Passed**: TX {tx.tx_id}: {from_w_label_display} → {to_w_label_display}")
        
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
    
    # Show info about selected transition if one is highlighted
    if "selected_transition" in st.session_state and st.session_state.selected_transition:
        sel = st.session_state.selected_transition
        from_w = sel.get("from_world", "?")
        to_w = sel.get("to_world", "?")
        proposal_id = sel.get("proposal_id", "?")
        try:
            _, worlds_dict, _ = load_worlds_and_valuation(examples_dir)
            from_label = format_world_label(from_w, worlds_dict)
            to_label = format_world_label(to_w, worlds_dict)
        except Exception:
            from_label = from_w
            to_label = to_w
        st.info(f"🔗 **Linked from Timeline**: The edge {from_label} → {to_label} will be highlighted in red below. **Note**: Edge highlighting is only visible in **Interactive (with hover tooltips)** view. Select a different transition in the **Governance History** tab to highlight a different edge.")
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
    
    # Graph view option
    graph_view = st.radio(
        "Graph View",
        ["Static Image", "Interactive (with hover tooltips)"],
        horizontal=True,
        help="Static Image: PNG visualization. Interactive: Plotly graph with hover tooltips showing world details."
    )
    
    if graph_view == "Interactive (with hover tooltips)" and PLOTLY_AVAILABLE:
        # Create interactive Plotly graph with tooltips
        import plotly.graph_objects as go
        import networkx as nx
        
        # Get layout positions (same as matplotlib for consistency)
        pos = nx.spring_layout(store.G, seed=7)
        
        # Determine visited worlds
        visited_worlds = set()
        if history_path and os.path.exists(history_path):
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    for h in history:
                        visited_worlds.add(h.get("from_world"))
                        visited_worlds.add(h.get("to_world"))
            except Exception:
                pass
        
        # Check for selected transition to highlight
        highlighted_edge = None
        if "selected_transition" in st.session_state and st.session_state.selected_transition:
            sel = st.session_state.selected_transition
            from_w = sel.get("from_world")
            to_w = sel.get("to_world")
            if from_w and to_w and (from_w, to_w) in store.G.edges():
                highlighted_edge = (from_w, to_w)
        
        # Prepare edge traces - separate highlighted edge from others
        edge_x = []
        edge_y = []
        highlighted_edge_x = []
        highlighted_edge_y = []
        
        for edge in store.G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            if edge == highlighted_edge:
                highlighted_edge_x.extend([x0, x1, None])
                highlighted_edge_y.extend([y0, y1, None])
            else:
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])
        
        # Regular edges trace
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=2, color='#888'),
            hoverinfo='none',
            mode='lines'
        )
        
        # Highlighted edge trace (if any)
        highlighted_trace = None
        if highlighted_edge_x:
            highlighted_trace = go.Scatter(
                x=highlighted_edge_x, y=highlighted_edge_y,
                line=dict(width=5, color='#ff4444'),  # Red, thicker line
                hoverinfo='none',
                mode='lines',
                name='Selected Transition'
            )
        
        # Prepare node traces with tooltips
        node_x = []
        node_y = []
        node_text = []
        node_info = []
        node_colors = []
        
        for node in store.G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            
            world = worlds[node]
            true_props = [p for p in props if model.is_true(p, node)]
            false_props = [p for p in props if p not in true_props]
            
            # Create tooltip text
            tooltip_parts = [
                f"<b>{node} ({world.name})</b>",
                f"<br>Description: {world.description}",
                "<br><br><b>Valuation:</b>",
            ]
            
            if true_props:
                tooltip_parts.append(f"<br>✓ True: {', '.join(true_props)}")
            if false_props:
                tooltip_parts.append(f"<br>✗ False: {', '.join(false_props)}")
            
            tooltip_parts.extend([
                "<br><br><b>Metadata:</b>",
                f"<br>Necessary: {', '.join(world.necessary) if world.necessary else 'None'}",
                f"<br>Possible: {', '.join(world.possible) if world.possible else 'None'}",
                f"<br>Edges: {', '.join(world.edges) if world.edges else 'None'}",
                f"<br>Arweave URI: {world.arweave_uri}",
                f"<br>Created by: {world.created_by}",
                f"<br>Created at: {world.created_at}",
            ])
            
            node_text.append(labels.get(node, node))
            node_info.append("".join(tooltip_parts))
            
            # Set color based on state
            if node == active_world:
                node_colors.append("#ffcc00")  # Yellow
            elif node in visited_worlds:
                node_colors.append("#90ee90")  # Green
            else:
                node_colors.append("#87ceeb")  # Blue
        
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=node_text,
            textposition="middle center",
            textfont=dict(size=10),
            hovertext=node_info,
            marker=dict(
                size=30,
                color=node_colors,
                line=dict(width=2, color='black')
            )
        )
        
        # Build figure data - include highlighted trace if it exists
        figure_data = [edge_trace, node_trace]
        if highlighted_trace:
            figure_data.insert(0, highlighted_trace)  # Add highlighted edge first so it's on top
        
        fig = go.Figure(data=figure_data,
                       layout=go.Layout(
                           title='',
                           showlegend=bool(highlighted_trace),  # Show legend if there's a highlighted edge
                           hovermode='closest',
                           margin=dict(b=20, l=5, r=5, t=40),
                           annotations=[dict(
                               text="Hover over nodes to see world details",
                               showarrow=False,
                               xref="paper", yref="paper",
                               x=0.005, y=-0.002,
                               xanchor="left", yanchor="bottom",
                               font=dict(size=12, color="#666")
                           )],
                           xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                           yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                           plot_bgcolor='white'
                       ))
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show highlighted edge info
        if highlighted_edge:
            sel = st.session_state.selected_transition
            from_w = sel.get("from_world", "?")
            to_w = sel.get("to_world", "?")
            proposal_id = sel.get("proposal_id", "?")
            try:
                _, worlds_dict, _ = load_worlds_and_valuation(examples_dir)
                from_label = format_world_label(from_w, worlds_dict)
                to_label = format_world_label(to_w, worlds_dict)
            except Exception:
                from_label = from_w
                to_label = to_w
            st.success(f"🔴 **Highlighted Edge**: {from_label} → {to_label} (Proposal: {proposal_id}) - This transition was selected from the Governance History tab.")
        
    elif graph_view == "Interactive (with hover tooltips)" and not PLOTLY_AVAILABLE:
        st.warning("⚠️ Plotly is not installed. Install it with: `pip install plotly` to enable interactive graphs with hover tooltips.")
        # Check if there's a selected transition and warn that highlighting won't work
        if "selected_transition" in st.session_state and st.session_state.selected_transition:
            st.warning("⚠️ **Note**: Edge highlighting is only available in Interactive mode. Switch to **Interactive (with hover tooltips)** view to see the selected transition highlighted.")
        st.image(graph_png_bytes(store.G, active_world, labels, history_path))
    else:
        # Static Image mode - warn if there's a selected transition
        if "selected_transition" in st.session_state and st.session_state.selected_transition:
            sel = st.session_state.selected_transition
            from_w = sel.get("from_world", "?")
            to_w = sel.get("to_world", "?")
            try:
                _, worlds_dict, _ = load_worlds_and_valuation(examples_dir)
                from_label = format_world_label(from_w, worlds_dict)
                to_label = format_world_label(to_w, worlds_dict)
            except Exception:
                from_label = from_w
                to_label = to_w
            st.warning(f"⚠️ **Note**: Edge highlighting is only visible in **Interactive (with hover tooltips)** mode. You have selected {from_label} → {to_label} from the Governance History tab. Switch to Interactive mode to see it highlighted in red.")
        st.image(graph_png_bytes(store.G, active_world, labels, history_path))
    
    # Add legend explaining node colors and edge highlighting
    st.markdown("**Node Colors:**")
    col1, col2, col3 = st.columns(3)
    col1.markdown("🟡 **Yellow**: Active world (current state)")
    col2.markdown("🟢 **Green**: Visited world (has been reached by a successful proposal)")
    col3.markdown("🔵 **Blue**: Unvisited world (not yet reached)")
    
    # Add edge legend if there's a highlighted edge (only in Interactive mode)
    if "selected_transition" in st.session_state and st.session_state.selected_transition:
        # Check if graph_view is defined and if we're in interactive mode
        try:
            is_interactive = graph_view == "Interactive (with hover tooltips)" and PLOTLY_AVAILABLE
        except (NameError, AttributeError):
            is_interactive = False
        
        if is_interactive:
            st.markdown("**Edge Highlighting:**")
            st.markdown("🔴 **Red thick edge**: Selected transition from Governance History tab (shows the direct impact of a successful vote). **Only visible in Interactive mode.**")
        else:
            st.markdown("**Edge Highlighting:**")
            st.markdown("🔴 **Red thick edge**: Available only in **Interactive (with hover tooltips)** mode. Switch to Interactive mode to see the selected transition highlighted.")
    
    st.divider()
    
    # World Details Section with Tooltip-like Information
    st.subheader("🔍 World Details (Hover Information)")
    st.markdown("Select a world to view its valuation (proposition states) and full metadata:")
    
    world_ids_list = sorted(worlds.keys())
    selected_world_id = st.selectbox(
        "Select a world to view details",
        world_ids_list,
        index=world_ids_list.index(active_world) if active_world in world_ids_list else 0,
        help="Select any world to see its valuation (which propositions are true) and full metadata (token data)"
    )
    
    if selected_world_id in worlds:
        selected_world = worlds[selected_world_id]
        
        # Get valuation for this world
        true_props = [p for p in props if model.is_true(p, selected_world_id)]
        false_props = [p for p in props if p not in true_props]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📊 Valuation (Proposition States)")
            st.markdown(f"**World**: {selected_world_id} ({selected_world.name})")
            
            if true_props:
                st.markdown("**True Propositions:**")
                for prop in true_props:
                    st.success(f"✓ {prop} = **True**")
            else:
                st.info("No propositions are true in this world")
            
            if false_props:
                st.markdown("**False Propositions:**")
                for prop in false_props:
                    st.error(f"✗ {prop} = **False**")
        
        with col2:
            st.markdown("### 🪙 World Metadata (Token Data)")
            from sim.tokenize import cip25_like_metadata
            metadata = cip25_like_metadata(selected_world)
            
            st.json(metadata)
        
        # Additional details
        with st.expander("📋 Detailed World Information"):
            st.markdown(f"**World ID**: `{selected_world.world_id}`")
            st.markdown(f"**Name**: {selected_world.name}")
            st.markdown(f"**Description**: {selected_world.description}")
            
            st.markdown("**Necessary Properties:**")
            if selected_world.necessary:
                st.code(", ".join(selected_world.necessary))
            else:
                st.info("None")
            
            st.markdown("**Possible Properties:**")
            if selected_world.possible:
                st.code(", ".join(selected_world.possible))
            else:
                st.info("None")
            
            st.markdown("**Possible Transitions (Edges):**")
            if selected_world.edges:
                edge_list = [f"{selected_world_id} → {edge}" for edge in selected_world.edges]
                st.code("\n".join(edge_list))
            else:
                st.info("No outgoing transitions")
            
            st.markdown("**Arweave URI**:")
            st.code(selected_world.arweave_uri)
            
            st.markdown("**Created By**:")
            st.code(selected_world.created_by)
            
            st.markdown("**Created At**:")
            st.code(selected_world.created_at)


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
    
    # Transition Selection for Graph Highlighting
    st.divider()
    st.subheader("🔗 Link to Graph Visualization")
    st.markdown(
        """
        **Select a transition below to highlight it in the Graph tab.** 
        This shows the direct impact of the vote by visually highlighting the edge (W2 → W3) that was successfully traversed.
        
        **Note**: Edge highlighting is only visible when viewing the graph in **Interactive (with hover tooltips)** mode in the Kripke Model Explorer tab.
        """
    )
    
    if history:
        # Load worlds for formatting
        try:
            _, worlds_dict, _ = load_worlds_and_valuation(examples_dir)
        except Exception:
            worlds_dict = {}
        
        # Create options for selectbox
        transition_options = []
        for idx, tx in enumerate(history, 1):
            from_world = tx.get("from_world", "?")
            to_world = tx.get("to_world", "?")
            proposal_id = tx.get("proposal_id", f"TX-{idx}")
            from_label = format_world_label(from_world, worlds_dict)
            to_label = format_world_label(to_world, worlds_dict)
            transition_options.append(f"TX {idx}: {proposal_id} ({from_label} → {to_label})")
        
        # Initialize session state for selected transition
        if "selected_transition_idx" not in st.session_state:
            st.session_state.selected_transition_idx = None
        
        # Get current selection index (default to last transition if none selected)
        default_idx = len(history) - 1 if st.session_state.selected_transition_idx is None else st.session_state.selected_transition_idx
        
        col_select, col_button = st.columns([3, 1])
        
        with col_select:
            selected_option = st.selectbox(
                "Select a transition to highlight in the Graph tab:",
                transition_options,
                index=default_idx if default_idx < len(transition_options) else 0,
                help="Choose a transition from the history to see it highlighted in the Kripke Model Explorer tab",
                key=f"transition_select_{history_signature}"
            )
        
        with col_button:
            st.write("")  # Spacing
            st.write("")  # Spacing
            if st.button("📍 View in Graph", type="primary", use_container_width=True):
                # Extract index from selected option
                selected_idx = transition_options.index(selected_option)
                st.session_state.selected_transition_idx = selected_idx
                st.session_state.selected_transition = {
                    "from_world": history[selected_idx].get("from_world"),
                    "to_world": history[selected_idx].get("to_world"),
                    "proposal_id": history[selected_idx].get("proposal_id"),
                    "index": selected_idx
                }
                st.success(f"✅ Transition selected! Switch to the **Kripke Model Explorer** tab to see the highlighted edge.")
                st.info("💡 **Tip**: The selected transition will remain highlighted until you select a different one or clear the selection.")
        
        # Show current selection info
        if "selected_transition" in st.session_state and st.session_state.selected_transition:
            sel = st.session_state.selected_transition
            from_w = sel.get("from_world", "?")
            to_w = sel.get("to_world", "?")
            from_label = format_world_label(from_w, worlds_dict)
            to_label = format_world_label(to_w, worlds_dict)
            st.info(f"📌 **Currently selected**: {from_label} → {to_label} (Proposal: {sel.get('proposal_id', '?')})")
        
        # Clear selection button
        if "selected_transition" in st.session_state and st.session_state.selected_transition:
            if st.button("🗑️ Clear Selection", use_container_width=False):
                st.session_state.selected_transition = None
                st.session_state.selected_transition_idx = None
                st.rerun()
    else:
        st.info("No transitions available yet. Run a simulation to generate transitions that can be highlighted in the graph.")
    
    # Visualizing Voting Results section
    st.divider()
    st.subheader("📊 Visualizing Voting Results")
    
    if history and PLOTLY_AVAILABLE:
        # Prepare data for visualizations
        transition_numbers = []
        proposal_ids = []
        from_worlds = []
        to_worlds = []
        votes_for_list = []
        votes_against_list = []
        participating_weights = []
        quorum_values = []
        estimated_total_weights = []
        
        for idx, tx in enumerate(history, 1):
            transition_numbers.append(idx)
            proposal_ids.append(tx.get("proposal_id", f"TX-{idx}"))
            from_worlds.append(tx.get("from_world", "?"))
            to_worlds.append(tx.get("to_world", "?"))
            votes_for = tx.get("votes_for", 0)
            votes_against = tx.get("votes_against", 0)
            votes_for_list.append(votes_for)
            votes_against_list.append(votes_against)
            participating_weight = votes_for + votes_against
            participating_weights.append(participating_weight)
            quorum = tx.get("quorum", 0.5)
            quorum_values.append(quorum)
            # Estimate total_possible_weight from quorum requirement
            # For successful transitions: participating_weight >= quorum * total_possible_weight
            # So: total_possible_weight <= participating_weight / quorum
            # We'll use the minimum estimate
            estimated_total = int(participating_weight / quorum) if quorum > 0 else participating_weight
            estimated_total_weights.append(estimated_total)
        
        # Vote Breakdown Pie Charts
        st.markdown("### Vote Breakdown by Transition")
        st.markdown("For each transition, see the distribution of voting weight: **For**, **Against**, and **Did Not Participate**.")
        
        # Create columns for pie charts (2 per row)
        num_transitions = len(history)
        if num_transitions > 0:
            # Calculate number of rows needed (2 charts per row)
            num_rows = (num_transitions + 1) // 2
            
            for row in range(num_rows):
                cols = st.columns(2)
                for col_idx in range(2):
                    tx_idx = row * 2 + col_idx
                    if tx_idx < num_transitions:
                        tx = history[tx_idx]
                        votes_for = votes_for_list[tx_idx]
                        votes_against = votes_against_list[tx_idx]
                        estimated_total = estimated_total_weights[tx_idx]
                        non_participating = max(0, estimated_total - votes_for - votes_against)
                        
                        # Create pie chart
                        labels = ['For', 'Against', 'Did Not Participate']
                        values = [votes_for, votes_against, non_participating]
                        colors = ['#28a745', '#dc3545', '#6c757d']  # Green, Red, Gray
                        
                        # Only show pie chart if there's data
                        if sum(values) > 0:
                            fig_pie = go.Figure(data=[go.Pie(
                                labels=labels,
                                values=values,
                                hole=0.3,
                                marker_colors=colors,
                                textinfo='label+percent+value',
                                texttemplate='%{label}<br>%{value}<br>(%{percent})',
                                hovertemplate='<b>%{label}</b><br>Weight: %{value}<br>Percentage: %{percent}<extra></extra>',
                            )])
                            
                            proposal_id = proposal_ids[tx_idx]
                            from_world = from_worlds[tx_idx]
                            to_world = to_worlds[tx_idx]
                            
                            fig_pie.update_layout(
                                title=f"TX {tx_idx + 1}: {proposal_id}<br>{from_world} → {to_world}",
                                height=350,
                                showlegend=True,
                                margin=dict(t=80, b=20, l=20, r=20),
                            )
                            
                            with cols[col_idx]:
                                st.plotly_chart(fig_pie, use_container_width=True)
                                
                                # Show detailed breakdown
                                with st.expander(f"Details for TX {tx_idx + 1}"):
                                    st.markdown(f"**Proposal ID**: {proposal_id}")
                                    st.markdown(f"**Transition**: {from_world} → {to_world}")
                                    st.markdown(f"**Votes For**: {votes_for} weight")
                                    st.markdown(f"**Votes Against**: {votes_against} weight")
                                    st.markdown(f"**Did Not Participate**: {non_participating} weight (estimated)")
                                    st.markdown(f"**Total Weight**: {estimated_total} (estimated from quorum requirement)")
                                    st.markdown(f"**Quorum**: {quorum_values[tx_idx]:.1%}")
                                    participation_pct = ((votes_for + votes_against) / estimated_total * 100) if estimated_total > 0 else 0
                                    st.markdown(f"**Participation**: {participation_pct:.1f}%")
                                    support_pct = (votes_for / (votes_for + votes_against) * 100) if (votes_for + votes_against) > 0 else 0
                                    st.markdown(f"**Support**: {support_pct:.1f}%")
            
            st.info("💡 **Note**: 'Did Not Participate' weight is estimated from the quorum requirement. The exact total voting weight is not stored in the transaction history.")
        
    elif history and not PLOTLY_AVAILABLE:
        st.warning("⚠️ Plotly is not installed. Install it with: `pip install plotly` to enable interactive voting visualizations.")
    else:
        st.info("No voting data to visualize yet. Run a simulation to generate transitions.")


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


with tab_modal:
    st.header("🔮 Modal Logic Explorer")
    
    st.markdown(
        """
        Explore modal logic formulas in the Kripke model. Evaluate formulas like **□p** (necessarily p) 
        and **◇p** (possibly p) to see which worlds satisfy the conditions.
        """
    )
    
    with st.expander("ℹ️ Understanding Modal Logic"):
        st.markdown(
            """
            **Modal Operators:**
            
            - **□p** (Box p, "Necessarily p"): True in world w if p is true in **all** reachable worlds from w.
            - **◇p** (Diamond p, "Possibly p"): True in world w if p is true in **at least one** reachable world from w.
            
            **Examples:**
            
            - **□p₁**: "Is p₁ true in all worlds we can reach from the current world?"
            - **◇p₃**: "Is it possible to reach a world where p₃ is true?"
            - **p₂**: "Is p₂ true in the current world?" (simple proposition)
            
            **Conventions:**
            - If a world has no successors, □p is **vacuously true** (all zero successors satisfy p).
            - If a world has no successors, ◇p is **false** (no successor satisfies p).
            """
        )
    
    # Load model and worlds
    try:
        store, worlds, model = load_worlds_and_valuation(examples_dir)
        props = sorted(list(model.valuation.keys()))
        world_ids = sorted(worlds.keys())
        
        # Get active world
        active = read_active()
        default_start_world = active.get("active_world", "w1")
        
        st.divider()
        
        # Formula input section
        st.subheader("📝 Enter Modal Formula")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            formula_input = st.text_input(
                "Modal Formula",
                value="◇p3",
                help="Enter a modal formula. Examples: □p1, ◇p2, p3, □◇p4"
            )
        
        with col2:
            start_world = st.selectbox(
                "Starting World",
                world_ids,
                index=world_ids.index(default_start_world) if default_start_world in world_ids else 0,
                help="The world from which to evaluate the formula"
            )
        
        # Parse and evaluate formula
        def parse_modal_formula(formula: str) -> tuple:
            """Parse a modal formula. Returns (operator, proposition) or (None, proposition) for simple props.
            
            Supports:
            - □p or Box p or necessarily p
            - ◇p or Diamond p or possibly p
            - p (simple proposition)
            """
            formula = formula.strip()
            
            # Check for Box (□)
            if formula.startswith("□") or formula.startswith("Box ") or formula.startswith("necessarily "):
                if formula.startswith("□"):
                    prop = formula[1:].strip()
                elif formula.startswith("Box "):
                    prop = formula[4:].strip()
                else:  # necessarily
                    prop = formula[11:].strip()
                return ("□", prop)
            
            # Check for Diamond (◇)
            if formula.startswith("◇") or formula.startswith("Diamond ") or formula.startswith("possibly "):
                if formula.startswith("◇"):
                    prop = formula[1:].strip()
                elif formula.startswith("Diamond "):
                    prop = formula[8:].strip()
                else:  # possibly
                    prop = formula[9:].strip()
                return ("◇", prop)
            
            # Simple proposition
            return (None, formula)
        
        def evaluate_formula(model: KripkeModel, formula: str, start_world: str) -> tuple:
            """Evaluate a modal formula. Returns (result, satisfying_worlds, explanation)."""
            operator, prop = parse_modal_formula(formula)
            
            if operator == "□":
                # Necessarily: true if prop is true in all successors
                result = model.is_necessary(prop, start_world)
                successors = model.successors(start_world)
                if not successors:
                    satisfying_worlds = set()
                    explanation = f"□{prop} is **vacuously true** in {start_world} (no successors)."
                else:
                    satisfying_worlds = {w for w in successors if model.is_true(prop, w)}
                    if result:
                        explanation = f"□{prop} is **true** in {start_world}: {prop} is true in all successors {successors}."
                    else:
                        failing = successors - satisfying_worlds
                        explanation = f"□{prop} is **false** in {start_world}: {prop} is false in {failing}."
                return (result, satisfying_worlds, explanation)
            
            elif operator == "◇":
                # Possibly: true if prop is true in at least one successor
                result = model.is_possible(prop, start_world)
                successors = model.successors(start_world)
                if not successors:
                    satisfying_worlds = set()
                    explanation = f"◇{prop} is **false** in {start_world} (no successors)."
                else:
                    satisfying_worlds = {w for w in successors if model.is_true(prop, w)}
                    if result:
                        explanation = f"◇{prop} is **true** in {start_world}: {prop} is true in {satisfying_worlds}."
                    else:
                        explanation = f"◇{prop} is **false** in {start_world}: {prop} is false in all successors {successors}."
                return (result, satisfying_worlds, explanation)
            
            else:
                # Simple proposition: true if prop is true in start_world
                result = model.is_true(prop, start_world)
                if result:
                    satisfying_worlds = {start_world}
                    explanation = f"{prop} is **true** in {start_world}."
                else:
                    satisfying_worlds = set()
                    explanation = f"{prop} is **false** in {start_world}."
                return (result, satisfying_worlds, explanation)
        
        # Evaluate button
        if st.button("🔍 Evaluate Formula", type="primary", use_container_width=True):
            if not formula_input:
                st.error("Please enter a formula.")
            else:
                try:
                    result, satisfying_worlds, explanation = evaluate_formula(model, formula_input, start_world)
                    
                    # Display result
                    st.divider()
                    st.subheader("📊 Evaluation Result")
                    
                    col_result1, col_result2 = st.columns([1, 2])
                    
                    with col_result1:
                        if result:
                            st.success(f"**Result: TRUE** ✓")
                        else:
                            st.error(f"**Result: FALSE** ✗")
                    
                    with col_result2:
                        st.markdown(explanation)
                    
                    # Show which worlds satisfy the condition
                    if satisfying_worlds:
                        st.markdown(f"**Worlds where condition is satisfied:** {', '.join(sorted(satisfying_worlds))}")
                    else:
                        st.info("No worlds satisfy this condition.")
                    
                    # Store result for visualization
                    st.session_state.modal_result = {
                        "formula": formula_input,
                        "start_world": start_world,
                        "result": result,
                        "satisfying_worlds": satisfying_worlds,
                        "explanation": explanation
                    }
                    
                except Exception as e:
                    st.error(f"Error evaluating formula: {str(e)}")
                    st.info("💡 **Tip**: Make sure the formula is valid. Examples: □p1, ◇p2, p3")
        
        # Visualization section
        st.divider()
        st.subheader("🗺️ Visual Representation")
        
        # Check if we have a result to visualize
        if "modal_result" in st.session_state:
            modal_result = st.session_state.modal_result
            
            # Create graph visualization with highlighted worlds
            if PLOTLY_AVAILABLE:
                import networkx as nx
                
                # Get layout positions
                pos = nx.spring_layout(store.G, seed=7)
                
                # Prepare edge traces
                edge_x = []
                edge_y = []
                for edge in store.G.edges():
                    x0, y0 = pos[edge[0]]
                    x1, y1 = pos[edge[1]]
                    edge_x.extend([x0, x1, None])
                    edge_y.extend([y0, y1, None])
                
                edge_trace = go.Scatter(
                    x=edge_x, y=edge_y,
                    line=dict(width=2, color='#888'),
                    hoverinfo='none',
                    mode='lines'
                )
                
                # Prepare node traces with highlighting
                node_x = []
                node_y = []
                node_text = []
                node_info = []
                node_colors = []
                
                satisfying_worlds = modal_result["satisfying_worlds"]
                start_world = modal_result["start_world"]
                
                for node in store.G.nodes():
                    x, y = pos[node]
                    node_x.append(x)
                    node_y.append(y)
                    
                    world = worlds[node]
                    true_props = [p for p in props if model.is_true(p, node)]
                    
                    # Create tooltip
                    tooltip_parts = [
                        f"<b>{node} ({world.name})</b>",
                        f"<br>True propositions: {', '.join(true_props) if true_props else 'None'}",
                    ]
                    
                    node_text.append(f"{node}")
                    node_info.append("".join(tooltip_parts))
                    
                    # Color coding:
                    # - Purple: Starting world
                    # - Green: Satisfying worlds (where condition is met)
                    # - Yellow: Active world (if different from start)
                    # - Blue: Other worlds
                    if node == start_world:
                        node_colors.append("#9b59b6")  # Purple for starting world
                    elif node in satisfying_worlds:
                        node_colors.append("#28a745")  # Green for satisfying worlds
                    elif node == active.get("active_world", "w1"):
                        node_colors.append("#ffcc00")  # Yellow for active world
                    else:
                        node_colors.append("#87ceeb")  # Blue for other worlds
                
                node_trace = go.Scatter(
                    x=node_x, y=node_y,
                    mode='markers+text',
                    hoverinfo='text',
                    text=node_text,
                    textposition="middle center",
                    textfont=dict(size=12, color='black'),
                    hovertext=node_info,
                    marker=dict(
                        size=40,
                        color=node_colors,
                        line=dict(width=3, color='black')
                    )
                )
                
                fig = go.Figure(data=[edge_trace, node_trace],
                               layout=go.Layout(
                                   title=f"Modal Formula: {modal_result['formula']} (from {start_world})",
                                   showlegend=False,
                                   hovermode='closest',
                                   margin=dict(b=20, l=5, r=5, t=60),
                                   annotations=[dict(
                                       text="Hover over nodes to see details",
                                       showarrow=False,
                                       xref="paper", yref="paper",
                                       x=0.005, y=-0.002,
                                       xanchor="left", yanchor="bottom",
                                       font=dict(size=12, color="#666")
                                   )],
                                   xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                   yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                   plot_bgcolor='white'
                               ))
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Legend
                st.markdown("**Node Colors:**")
                col_leg1, col_leg2, col_leg3, col_leg4 = st.columns(4)
                col_leg1.markdown("🟣 **Purple**: Starting world")
                col_leg2.markdown("🟢 **Green**: Worlds satisfying condition")
                col_leg3.markdown("🟡 **Yellow**: Active world")
                col_leg4.markdown("🔵 **Blue**: Other worlds")
                
            else:
                st.warning("⚠️ Plotly is not installed. Install it with: `pip install plotly` to enable interactive graph visualization.")
        else:
            st.info("👆 Enter a formula and click 'Evaluate Formula' to see the visualization.")
        
        # Available propositions
        st.divider()
        st.subheader("📚 Available Propositions")
        st.markdown(f"The following propositions are available in the model: **{', '.join(props)}**")
        
        with st.expander("See proposition valuations"):
            valuation_data = []
            for world_id in world_ids:
                world_label = format_world_label(world_id, worlds)
                row = {"World": world_label}
                for prop in props:
                    is_true = model.is_true(prop, world_id)
                    row[prop] = "✓" if is_true else "✗"
                valuation_data.append(row)
            st.dataframe(valuation_data, width='stretch', use_container_width=True, hide_index=False)
    
    except Exception as e:
        st.error(f"Error loading model: {str(e)}")
        st.info("💡 Make sure the graph is initialized. Go to the **System Status & Setup** tab and click 'Initialize Example Graph'.")


