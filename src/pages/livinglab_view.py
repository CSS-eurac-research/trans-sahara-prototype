import streamlit as st
import json
import os
from streamlit.components.v1 import html as st_html
from src.core.map_utils import build_damongo_sites_map


def render_livinglab_view():
    """Render the Living Lab view with the Damongo sites map."""
    st.title("Livinglab View: Ghana Living Lab - Damango")

    top_left, top_right = st.columns([1, 3])
    with top_left:
        if st.button("← Back to initial page", type="secondary"):
            st.session_state.session_started = False
            st.rerun()
        if st.button("Legend", type="secondary"):
            st.session_state.in_session_page = "Legend"
            st.rerun()
        if st.button("WEFE Analysis", type="primary"):
            st.session_state.in_session_page = "WEFE Analysis"
            st.rerun()

    geojson_path = os.path.join("data", "geo", "damongo_sites.geojson")
    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            damongo_geo = json.load(f)
    except Exception as e:
        damongo_geo = None
        st.warning(f"Could not load Damongo sites: {e}")

    m, _bounds = build_damongo_sites_map(damongo_geo)

    left_col, right_col = st.columns([1, 1])
    with left_col:
        st.empty()
    with right_col:
        st_html(m._repr_html_(), height=900)


