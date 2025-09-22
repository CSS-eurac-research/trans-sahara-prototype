import streamlit as st
from src.pages.livinglab_view import render_livinglab_view
from src.pages.wefe_analysis import render_wefe_analysis


def render_session_page():
    if st.button("← Back to initial page", type="secondary"):
        st.session_state.session_started = False
        st.rerun()
    tabs = st.tabs(["Livinglab View", "WEFE Analysis"])

    with tabs[0]:
        render_wefe_analysis()

    with tabs[1]:
        render_livinglab_view()


