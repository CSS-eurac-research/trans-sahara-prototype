import streamlit as st
import os
import base64
from src.core.data_loader import initialize_session_state
from src.pages.initial_page import render_sidebar_welcome_page, render_welcome_page
from src.pages.livinglab_view import render_livinglab_view
from src.pages.wefe_analysis import render_wefe_analysis
from src.pages.legend import render_legend_page

def render_footer():
    """Render the footer of the app"""
    footer_logo_b64 = ""
    try:
        with open("assets/founded-logo.jpg", "rb") as f:
            footer_logo_b64 = base64.b64encode(f.read()).decode()
    except Exception:
        pass

    st.markdown(
        """
        <style>
            .app-footer { background: #ffffff; border-top: 1px solid #e6e6e6; padding: 10px 16px; margin-top: 12px; }
            .app-footer .footer-inner { display: flex; align-items: center; justify-content: center; gap: 16px; }
            .app-footer .footer-text { font-size: 12px; color: #333333; }
            .app-footer img { height: 40px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class=\"app-footer\">
            <div class=\"footer-inner\">
                {('<img src=\"data:image/jpeg;base64,' + footer_logo_b64 + '\" alt=\"EU logo\"/>') if footer_logo_b64 else ''}
                <div class=\"footer-text\">
                    Funded by the European Union under the Horizon Europe Framework Programme Grant Agreement Nº: 101182176. Views and opinions expressed are however those of the author(s) only and do not necessarily reflect those of the European Union or of the European Research Executive Agency. Neither the European Union nor the granting authority can be held responsible for them.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Layout and session state initialization
st.set_page_config(layout="wide", page_title="Trans-Sahara Support Tool")
initialize_session_state()

if not st.session_state.session_started:
    try:
        st.sidebar.image("assets/transahara-logo-fullcolor.jpg", use_container_width=True)
    except Exception:
        st.sidebar.markdown("**Trans-Sahara**")


if st.session_state.session_started:
    # Use session state to route between in-session pages, avoid rendering sidebar
    page = st.session_state.get("in_session_page", "Livinglab View")
    if page == "Legend":
        render_legend_page()
    elif page == "WEFE Analysis":
        render_wefe_analysis()
    else:
        render_livinglab_view()
else:
    render_sidebar_welcome_page()
    if st.session_state.get("pre_nav") == "Legend":
        render_legend_page()
    else:
        render_welcome_page()

render_footer()


