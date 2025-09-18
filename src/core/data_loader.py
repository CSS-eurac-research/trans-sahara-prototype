"""
General data loading functionality
"""
import json
import os
import pandas as pd
import streamlit as st


def load_living_labs():
    """Load living labs data from per-lab directories if available, otherwise fallback to legacy JSON file.

    New structure:
    data/
      livinglabs/
        <lab_slug>/
          lab.json
    """
    base_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
    livinglabs_dir = os.path.join(base_dir, 'livinglabs')

    labs: list[dict] = []
    if os.path.isdir(livinglabs_dir):
        try:
            for entry in sorted(os.listdir(livinglabs_dir)):
                lab_dir = os.path.join(livinglabs_dir, entry)
                if not os.path.isdir(lab_dir):
                    continue
                lab_file = os.path.join(lab_dir, 'lab.json')
                if os.path.isfile(lab_file):
                    with open(lab_file, 'r', encoding='utf-8') as f:
                        lab = json.load(f)
                        if isinstance(lab, dict):
                            # Attach optional resources file if present
                            resources_file = os.path.join(lab_dir, 'lab_resources_info.json')
                            if os.path.isfile(resources_file):
                                try:
                                    with open(resources_file, 'r', encoding='utf-8') as rf:
                                        lab_resources = json.load(rf)
                                        if isinstance(lab_resources, dict):
                                            lab['resources'] = lab_resources
                                except Exception:
                                    pass
                            labs.append(lab)
        except Exception:
            labs = []

    if labs:
        return labs

    # Fallback to legacy single-file structure
    legacy_path = os.path.join(base_dir, 'livinglab.json')
    with open(legacy_path, "r", encoding="utf-8") as f:
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


def load_crops() -> dict:
    """Load crops list from data/crops.json.

    Returns a dict with keys 'food' and 'non-food'.
    """
    data_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'crops.json')
    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)
