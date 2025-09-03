import base64
import streamlit as st
import folium
from folium import plugins
import pandas as pd
from src.core.data_loader import load_living_labs, get_regions_from_labs
from src.core.wefe_calculations import PILLARS, calculate_kpi_scores, calculate_overall_wefe_score_from_kpis, get_indicator_units, format_indicator_with_unit, get_kpi_def_summaries, get_indicator_display_names
import streamviz
from src.policy.data import get_indicator_numbering, get_indicator_with_number

def create_living_labs_map(selected_lab=None):
    """Create an interactive map showing all living lab areas as squares"""
    livinglabs = load_living_labs()
    
    # Map settings
    center_lat = 18.0
    center_lon = 10.0
    zoom_level = 3.5   
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_level,
        tiles='OpenStreetMap'
    )
    
    # Add each living lab area as a rectangle
    for lab in livinglabs:
        upper_left = lab['geolocation_area']['upper_left']
        lower_right = lab['geolocation_area']['lower_right']
        
        rectangle_coords = [
            [upper_left['lat'], upper_left['lon']],
            [upper_left['lat'], lower_right['lon']],
            [lower_right['lat'], lower_right['lon']],
            [lower_right['lat'], upper_left['lon']],
            [upper_left['lat'], upper_left['lon']]
        ]
        if selected_lab and lab['name'] == selected_lab:
            color = 'blue'  # Selected lab
            weight = 3
        else:
            color = 'red'   # Unselected labs
            weight = 2
        
        folium.Polygon(
            locations=rectangle_coords,
            color=color,
            weight=weight,
            fill=True,
            fillColor=color,
            fillOpacity=0.3,
            popup=f"<b>{lab['name']}</b><br>Country: {lab['country']}<br>Climate: {lab['climate_type']}"
        ).add_to(m)
        
    return m

def get_selected_lab_info(selected_lab_name):
    """Get detailed information about the selected living lab"""
    if not selected_lab_name:
        return None
    
    livinglabs = load_living_labs()
    for lab in livinglabs:
        if lab['name'] == selected_lab_name:
            return lab
    return None

def render_sidebar_welcome_page():
    """Render the initial setup page with sidebar configuration"""
    st.sidebar.header("1. Select Living Lab and Impact Weights")

    livinglabs = load_living_labs()
    regions = get_regions_from_labs(livinglabs)
    
    selected_lab = st.sidebar.selectbox("Select a Living Lab", regions, key="select_lab")
    st.session_state.current_selected_lab = selected_lab
    st.sidebar.markdown("---")
    
    # Inject CSS to style ONLY the first sidebar expander (WEFE weights) with red border and red title
    st.sidebar.markdown(
        """
        <style>
        section[data-testid=\"stSidebar\"] div[data-testid=\"stExpander\"]:first-of-type {
            border: 2px solid #e74c3c !important;
            border-radius: 8px !important;
        }
        section[data-testid=\"stSidebar\"] div[data-testid=\"stExpander\"]:first-of-type button,
        section[data-testid=\"stSidebar\"] div[data-testid=\"stExpander\"]:first-of-type div[role=\"button\"] {
            color: #e74c3c !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # WEFE weights settings
    with st.sidebar.expander("WEFE weights settings", expanded=False):
        st.markdown("<span style='color:#e74c3c;font-weight:700;'>WILL BE REMOVED</span>", unsafe_allow_html=True)
        water_w = st.slider("Water", 0, 5, 3, key="water_weight")
        energy_w = st.slider("Energy", 0, 5, 3, key="energy_weight")
        food_w = st.slider("Food", 0, 5, 3, key="food_weight")
        eco_w = st.slider("Ecosystems", 0, 5, 3, key="eco_weight")
    
    # Store current weights in session state immediately (not just when session starts)
    st.session_state.policy_weights = {
        "Water": water_w, "Energy": energy_w, "Food": food_w, "Ecosystem": eco_w
    }

    # Session parameters settings 
    with st.sidebar.expander("Session parameters settings", expanded=False):
        budget = st.number_input("Budget (Million USD)", 0, 1000, 10, 1, key="budget")
        time_range = st.number_input("End of simulation", 2030, 2100, 2030, 5, key="sim_year")

    # Scenario definition settings
    with st.sidebar.expander("Scenario definition", expanded=False):
        st.markdown("Here it's possible to pick a specific scenario if needed for the analysis")
        scenario_options = ["Baseline", "Climate Change", "Population Growth", "Technology Adoption"]
        selected_scenario = st.selectbox("Select Scenario", scenario_options, key="scenario_select")

    if st.sidebar.button("Start Session", key="start_session"):
        st.session_state.session_started = True
        st.session_state.selected_lab = selected_lab
        # Weights are already stored above, no need to set them again here
        st.rerun()

def render_wefe_pillars_view(lab_info):
    """Render a card-style view for all 4 WEFE pillars of the selected living lab."""
    if not lab_info:
        st.info("No WEFE data available for this living lab.")
        return

    pillars = PILLARS
    units_dict = get_indicator_units()
    indicator_names = get_indicator_display_names()

    cols = st.columns(4)
    for i, pillar in enumerate(pillars):
        data = lab_info.get('kpi_indicators', {})
        
        with cols[i]:
            with st.container(border=True):
                internal_col1, internal_col2 = st.columns([1, 2])
                with internal_col1:
                    st.markdown(f"<div style='display:flex;align-items:center;'><span style='font-size:2rem;'>{pillar['icon']}</span> <span style='font-size:2rem;font-weight:700;margin-left:0.5em;color:{pillar['color']}'>{pillar['label']}</span></div>", unsafe_allow_html=True)
                # no per-pillar score
                # Show KPI indicators relevant for this pillar
                st.divider()
                # Determine indicators for this pillar from new_pillars.json units dict keys
                for ind_name in sorted(units_dict.keys()):
                    # crude filter by prefix convention IND_<PILLARLETTER>_
                    if pillar["key"] == 'water' and ind_name.startswith('IND_W_') \
                       or pillar["key"] == 'energy' and ind_name.startswith('IND_E_') \
                       or pillar["key"] == 'food' and ind_name.startswith('IND_F_'):
                        if ind_name in data:
                            ind_value = data[ind_name]
                            formatted_value = format_indicator_with_unit(ind_name, ind_value, units_dict)
                            display_name = indicator_names.get(ind_name, ind_name)
                            st.markdown(f"**{display_name}**: {formatted_value}")
    
    with cols[3]:
        with st.container(border=True):
            st.markdown(f"<div style='display:flex;align-items:center;'><span style='font-size:2rem;'>🌿</span> <span style='font-size:2rem;font-weight:700;margin-left:0.5em;color:{pillar['color']}'>Ecosystems</span></div>", unsafe_allow_html=True)


def render_overall_wefe_score(lab_info):
    """Render the overall WEFE Nexus score container"""
    if not lab_info or 'wefe_pillars' not in lab_info:
        return
    
    # Get weights from session state (from sidebar settings)
    # These should always be available now since they're set in the sidebar function
    weights = st.session_state.get('policy_weights', {
        "Water": 3, "Energy": 3, "Food": 3, "Ecosystem": 3
    })
    
    # Calculate KPI scores and overall WEFE score from KPIs
    overall_score, breakdown = calculate_overall_wefe_score_from_kpis(lab_info)
    
    if overall_score is not None:
        # Create the main container
        with st.container(border=True):
            # Header row
            col1, col2 = st.columns([3, 2])
            
            with col1:
                st.markdown(
                    """
                    <div style='display: flex; align-items: center; margin-bottom: 10px;'>
                        <span style='font-size: 2rem; margin-right: 15px;'>🌍</span>
                        <div>
                            <h2 style='margin: 0; color: #2E86AB; font-size: 1.8rem;'>WEFE NEXUS Evaluation</h2>
                            <p style='margin: 0; color: #666; font-size: 0.9rem;'>Overall sustainability score based on weighted pillar assessment</p>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            # with col2:
                # streamviz.gauge(overall_score / 100, gSize="SML", sFix="%", gcHigh="#f39c12", gcLow="#e74c3c", gcMid="#27ae60")
            with col2:
                # Overall score display
                score_color = "#27ae60" if overall_score >= 70 else "#f39c12" if overall_score >= 50 else "#e74c3c"
                st.markdown(
                    f"""
                    <div style='text-align: center; padding: 10px; background-color: {score_color}; border-radius: 10px; color: white;'>
                        <div style='font-size: 0.9rem; font-weight: 500;'>Overall Score</div>
                        <div style='font-size: 2.5rem; font-weight: bold; line-height: 1;'>{overall_score}</div>
                        <div style='font-size: 0.8rem; opacity: 0.9;'>/ 100</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            # KPI selection and display of affecting indicators
            kpi_scores = breakdown.get("kpi_scores", {})
            if kpi_scores:
                kpi_defs = get_kpi_def_summaries()
                indicator_names = get_indicator_display_names()

                # Build options with a default "None"
                kpi_options = ["None"] + [
                    f"{kpi_id} - {kpi_defs.get(kpi_id, {}).get('name', kpi_id)}"
                    for kpi_id in sorted(kpi_scores.keys())
                ]

                selected_option = st.selectbox(
                    "Select a KPI to view its affecting indicators",
                    kpi_options,
                    index=0,
                    key="kpi_select_inspect"
                )

                if selected_option != "None":
                    selected_kpi_id = selected_option.split(" - ", 1)[0]
                    selected_meta = kpi_defs.get(selected_kpi_id, {"name": selected_kpi_id, "inputs": []})
                    affecting_inds = selected_meta.get("inputs", [])

                    st.markdown(f"**KPI:** {selected_meta.get('name', selected_kpi_id)}")
                    if affecting_inds:
                        st.markdown("**Indicators affecting this KPI:**")
                        for ind_id in affecting_inds:
                            human = indicator_names.get(ind_id, ind_id)
                            st.markdown(f"- {human}")
                    else:
                        st.info("No indicator inputs defined for this KPI.")
    

def render_welcome_page():
    """Render the welcome page when session hasn't started"""
    
    selected_lab = st.session_state.get('current_selected_lab', None)
    
    col1, col2 = st.columns([3, 2])    
    

    with col1:
        if selected_lab:
            lab_info = get_selected_lab_info(selected_lab)
            if lab_info:
                st.subheader(f"**{lab_info['name']}**")
                st.markdown(f"**Country:** {lab_info['country']}")
                st.markdown(f"**Climate Type:** {lab_info['climate_type']}")
                st.markdown(f"**Description:** {lab_info['description']}")
                
                if 'surface_m3' in lab_info:
                    st.markdown(f"**Total Surface:** {lab_info['surface_m3']} m³")
                
                if 'challenges' in lab_info and lab_info['challenges']:
                    with st.expander("⚠️ Main Challenges", expanded=False):
                        st.markdown("**Main challenges of the living lab:**")
                        for i, challenge in enumerate(lab_info['challenges'], 1):
                            st.markdown(f"- {challenge}")
                
                land_use = lab_info.get('land_use_surfaces_m3', {})
                if land_use:
                    total_surface = lab_info.get('surface_m3') or sum(land_use.values())
                    table_rows = [
                        {"Land Use": "Residential", "Surface (m³)": land_use.get("residential", 0)},
                        {"Land Use": "Mixed", "Surface (m³)": land_use.get("mixed", 0)},
                        {"Land Use": "Green", "Surface (m³)": land_use.get("green", 0)},
                        {"Land Use": "Water", "Surface (m³)": land_use.get("water", 0)},
                    ]
                    df_land_use = pd.DataFrame(table_rows)
                    if total_surface and total_surface > 0:
                        df_land_use["Share (%)"] = (df_land_use["Surface (m³)"] / float(total_surface) * 100)
                    else:
                        df_land_use["Share (%)"] = 0.0
                    
                    styled_df = df_land_use.style.format({"Share (%)": "{:.1f} %"})
                    st.markdown("**Land Use Surfaces**")
                    st.dataframe(styled_df, use_container_width=True)
                
            else:
                lab_info = None
        else:
            st.subheader("Living Lab Information")
            st.info("Select a living lab from the sidebar to view its details.")
            lab_info = None
    with col2:
        map_obj = create_living_labs_map(selected_lab)
        st.components.v1.html(map_obj._repr_html_(), height=500, width=None)
    
    render_overall_wefe_score(lab_info)
    render_wefe_pillars_view(lab_info) 
    
    
    
