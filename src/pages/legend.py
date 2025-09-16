import json
import os
import streamlit as st


def render_legend_page():
    """Render the Legend page from data/legend.json, grouped by category."""
    st.title("Legend")

    # In-session back button to livinglab view
    left, _ = st.columns([1, 3])
    with left:
        if st.button("← Back to Livinglab View", type="secondary"):
            st.session_state.in_session_page = "Livinglab View"
            st.rerun()

    legend_path = os.path.join("data", "legend.json")
    try:
        with open(legend_path, "r", encoding="utf-8") as f:
            legend = json.load(f)
    except Exception as e:
        st.error(f"Unable to load legend.json: {e}")
        legend = {}

    if not isinstance(legend, dict) or not legend:
        st.info("No legend entries available.")
        return

    for category, entries in legend.items():
        with st.container(border=True):
            st.subheader(category)
            if isinstance(entries, dict):
                for term, description in entries.items():
                    st.markdown(f"**{term}**: {description}")
            else:
                st.write(entries)


