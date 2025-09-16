"""
General data loading functionality
"""
import json
import os
import pandas as pd
import streamlit as st


def load_living_labs():
    """Load living labs data from JSON file"""
    data_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'livinglab.json')
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_regions_from_labs(livinglabs):
    """Extract region names from living labs data"""
    return [lab["name"] for lab in livinglabs]


def initialize_session_state():
    """Initialize all session state variables"""
    if "session_started" not in st.session_state:
        st.session_state.session_started = False
    if "current_selected_lab" not in st.session_state:
        st.session_state.current_selected_lab = None
    if "selected_lab" not in st.session_state:
        st.session_state.selected_lab = "Ghana Living Lab - Damango"  # Default lab
    # Remove policy/intervention states
    if "selected_policies" in st.session_state:
        del st.session_state["selected_policies"]
    if "policy_inputs" in st.session_state:
        del st.session_state["policy_inputs"]
    if "policy_suggestions" in st.session_state:
        del st.session_state["policy_suggestions"]
    if "active_interventions" in st.session_state:
        del st.session_state["active_interventions"]


def get_map_data():
    """Get default map data for Tunisia"""
    return pd.DataFrame({"lat": [34.8], "lon": [10.1]})
