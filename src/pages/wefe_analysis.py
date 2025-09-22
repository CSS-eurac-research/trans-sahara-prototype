import os
import json
import streamlit as st
from src.core.data_loader import load_crops


def _format_crop_info_markdown(info: dict, name: str) -> str:
    ideal_ph = (info or {}).get("ideal_soil_ph") or {}
    ideal_temp = (info or {}).get("ideal_temp_c") or {}
    yield_days = (info or {}).get("yield_period_days")
    avg_yield = (info or {}).get("average_yield_g_per_week")
    water = (info or {}).get("water_required_l_per_kg_per_month")
    space = (info or {}).get("space_m2_per_seed")

    lines = [
        f"**Crop**: {info.get('name', name)}\n\n",
        f"- pH ideal range: {ideal_ph.get('min','-')} - {ideal_ph.get('max','-')}\n",
        f"- Water: {water if water is not None else '-'} L/kg/month\n",
        f"- Spacing: {space if space is not None else '-'} m²/seed\n",
        f"- Temp ideal: {ideal_temp.get('min','-')} - {ideal_temp.get('max','-')} °C\n",
    ]
    if yield_days is not None:
        lines.append(f"- Yield period: {yield_days} days\n")
    if avg_yield is not None:
        lines.append(f"- Avg. yield: {avg_yield} g/week\n")
    return "".join(lines)


def _render_crop_group(title: str, names: list[str], crop_info_map: dict[str, dict]):
    st.subheader(title)
    for name in names:
        current_value = st.session_state.wefe_crop_self_sufficiency.get(name, 0)
        enabled = st.session_state.wefe_crop_enabled.get(name, False)

        left, right = st.columns([1, 3])
        with left:
            enabled = st.checkbox(name, value=enabled, key=f"wefe_crop_chk_{name}")
            st.session_state.wefe_crop_enabled[name] = enabled
        with right:
            num_col, info_col = st.columns([6, 1])
            with num_col:
                new_val = st.number_input(
                    label=f"{name} (%)",
                    min_value=0,
                    max_value=100,
                    value=int(current_value),
                    step=1,
                    disabled=not enabled,
                    label_visibility="collapsed",
                    key=f"wefe_crop_num_{name}"
                )
            with info_col:
                info = crop_info_map.get(name, {"name": name})
                md = _format_crop_info_markdown(info, name)
                if hasattr(st, "popover"):
                    with st.popover("ℹ️", use_container_width=True):
                        st.markdown(md)
                else:
                    with st.expander("ℹ️ Info", expanded=False):
                        st.markdown(md)
        if enabled:
            st.session_state.wefe_crop_self_sufficiency[name] = int(new_val)


def render_wefe_analysis():
    st.title("WEFE Analysis")

    crops = load_crops()
    food_list = crops.get("food", [])
    non_food_list = crops.get("non-food", [])

    crop_info_map = {}
    for c in food_list + non_food_list:
        if isinstance(c, dict):
            name = c.get("name", "")
            if name:
                crop_info_map[name] = c
        else:
            crop_info_map[str(c)] = {"name": str(c)}
    
    food_names = [c if isinstance(c, str) else c.get("name", "") for c in food_list]
    non_food_names = [c if isinstance(c, str) else c.get("name", "") for c in non_food_list]

    # Session state for selections and percentages
    if "wefe_selected_crop" not in st.session_state:
        st.session_state.wefe_selected_crop = None
    if "wefe_crop_self_sufficiency" not in st.session_state:
        st.session_state.wefe_crop_self_sufficiency = {}
    if "wefe_crop_enabled" not in st.session_state:
        st.session_state.wefe_crop_enabled = {}
    if "wefe_water_shares" not in st.session_state:
        st.session_state.wefe_water_shares = {"groundwater": 0, "treated_wastewater": 0, "surface_water": 0}
    if "wefe_energy_shares" not in st.session_state:
        st.session_state.wefe_energy_shares = {"gasoline": 0, "hydropower": 0, "wind": 0, "solar": 0, "diesel": 0}

    row1_col1, row1_col2, row1_col3 = st.columns([1, 1, 1])

    try:
        pillars_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'pillars.json')
        with open(pillars_path, 'r', encoding='utf-8') as pf:
            pillars_json = json.load(pf).get('wefe_pillars', {})
    except Exception:
        pillars_json = {}
    food_meta = pillars_json.get('food', {"icon": "🌾", "color": "#27ae60", "label": "Food"})
    water_meta = pillars_json.get('water', {"icon": "💧", "color": "#3498db", "label": "Water"})
    energy_meta = pillars_json.get('energy', {"icon": "⚡", "color": "#f39c12", "label": "Energy"})

    with row1_col1:
        with st.container(border=True):
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:8px;'>"
                f"<span style='font-size:1.6rem'>{food_meta.get('icon','')}</span>"
                f"<span style='font-size:1.4rem;font-weight:700;color:{food_meta.get('color','#27ae60')}'>Crop self-sufficiency (%)</span>"
                f"</div>",
                unsafe_allow_html=True
            )
            _render_crop_group("Food crops", food_names, crop_info_map)
            _render_crop_group("Non-food crops", non_food_names, crop_info_map)

    with row1_col2:
        with st.container(border=True):
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:8px;'>"
                f"<span style='font-size:1.6rem'>{water_meta.get('icon','')}</span>"
                f"<span style='font-size:1.4rem;font-weight:700;color:{water_meta.get('color','#3498db')}'>Water source shares (%)</span>"
                f"</div>",
                unsafe_allow_html=True
            )
            for src in ["groundwater", "treated_wastewater", "surface_water"]:
                val = st.session_state.wefe_water_shares.get(src, 0)
                new_val = st.number_input(src.replace("_", " ").title(), min_value=0, max_value=100, value=int(val), step=1, key=f"wefe_water_{src}")
                if new_val != val:
                    st.session_state.wefe_water_shares[src] = new_val
            # Validate total equals 100
            water_total = sum(int(v) for v in st.session_state.wefe_water_shares.values())
            if water_total > 100:
                st.error(f"Water shares total {water_total}%. Reduce values to 100%.")
            elif water_total != 100:
                st.warning(f"Water shares total {water_total}%. Adjust to 100%.")

    with row1_col2:
        with st.container(border=True):
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:8px;'>"
                f"<span style='font-size:1.6rem'>{energy_meta.get('icon','')}</span>"
                f"<span style='font-size:1.4rem;font-weight:700;color:{energy_meta.get('color','#f39c12')}'>Energy source shares (%)</span>"
                f"</div>",
                unsafe_allow_html=True
            )
            for src in ["gasoline", "hydropower", "wind", "solar", "diesel"]:
                val = st.session_state.wefe_energy_shares.get(src, 0)
                new_val = st.number_input(src.title(), min_value=0, max_value=100, value=int(val), step=1, key=f"wefe_energy_{src}")
                if new_val != val:
                    st.session_state.wefe_energy_shares[src] = new_val
            # Validate total equals 100
            energy_total = sum(int(v) for v in st.session_state.wefe_energy_shares.values())
            if energy_total > 100:
                st.error(f"Energy shares total {energy_total}%. Reduce values to 100%.")
            elif energy_total != 100:
                st.warning(f"Energy shares total {energy_total}%. Adjust to 100%.")
    with row1_col3:
        st.title("Comparison between different strategies")


