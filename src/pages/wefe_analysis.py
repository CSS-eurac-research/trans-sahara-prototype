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


def _render_crop_group(title: str, names: list[str], crop_info_map: dict[str, dict], defaults_map: dict[str, dict]):
    st.subheader(title)
    header = st.columns([1, 2, 2, 3, 1])
    with header[0]:
        st.markdown("**Select**")
    with header[1]:
        st.markdown("**Crop**")
    with header[2]:
        st.markdown("**Starting self-sufficiency**")
    with header[3]:
        st.markdown("**New self-sufficiency (%)**")
    with header[4]:
        st.markdown("**Info**")

    for name in names:
        current_value = st.session_state.wefe_crop_self_sufficiency.get(name, 0)
        enabled = st.session_state.wefe_crop_enabled.get(name, False)
        default_meta = (defaults_map or {}).get(name, {})
        default_pct = default_meta.get('default_percent')
        default_label = f"~{default_pct:.0f}%" if isinstance(default_pct, (int, float)) else "n/a"

        row = st.columns([1, 2, 2, 3, 1])
        with row[0]:
            enabled_new = st.checkbox(
                label=f"select_{name}",
                value=enabled,
                key=f"wefe_crop_sel_{name}",
                label_visibility="collapsed"
            )
            enabled = enabled_new
            st.session_state.wefe_crop_enabled[name] = enabled
        with row[1]:
            st.markdown(name)
        with row[2]:
            st.markdown(default_label)
        with row[3]:
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
        with row[4]:
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


def _load_damango_lab_and_resources():
    try:
        base = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'livinglabs', 'ghana_damango')
        with open(os.path.join(base, 'lab.json'), 'r', encoding='utf-8') as lf:
            lab = json.load(lf)
        with open(os.path.join(base, 'lab_resources_info.json'), 'r', encoding='utf-8') as rf:
            resources = json.load(rf)
        return lab, resources
    except Exception:
        return None, None


def calculate_self_sufficiency(crop_info_map: dict[str, dict]) -> dict[str, dict]:
    """
    Compute default self-sufficiency for enabled crops across the Damango living lab.

    Returns a map: { crop_name: { 'default_percent': number|None, 'status': 'computed'|'n/a' } }
    - Non-preselected crops are returned with status 'n/a' and default_percent None.
    """
    lab, resources = _load_damango_lab_and_resources()
    result: dict[str, dict] = {}
    if not lab or not resources:
        return result

    # Build annual consumption map (tonnes/year -> kg/year)
    consumption_list = (resources.get('food') or [])
    crop_to_consumption_kg_per_year: dict[str, float] = {}
    for entry in consumption_list:
        if not isinstance(entry, dict):
            continue
        name = entry.get('name')
        val_tonnes = entry.get('annual_consumption')
        if isinstance(name, str) and isinstance(val_tonnes, (int, float)):
            crop_to_consumption_kg_per_year[name] = float(val_tonnes) * 1000.0

    # Area allocation from lab crop_distribution
    crop_to_area_m2: dict[str, float] = {}
    for site in lab.get('sites', []):
        props = site or {}
        total_area_m2 = float(props.get('surface_m3', 0) or 0)
        land_cover = props.get('land_cover_percent', {}) or {}
        green_pct = float(land_cover.get('green', 0) or 0)
        green_area_m2 = total_area_m2 * (max(0.0, min(1.0, green_pct / 100.0)))
        for dist in (props.get('crop_distribution') or []):
            name = dist.get('name')
            share_pct = float(dist.get('green_share_percent', 0) or 0)
            if not isinstance(name, str) or name.lower() == 'unused greenland':
                continue
            crop_to_area_m2[name] = crop_to_area_m2.get(name, 0.0) + green_area_m2 * (max(0.0, min(1.0, share_pct / 100.0)))

    # Compute default self-sufficiency for enabled crops
    enabled_map = st.session_state.get('wefe_crop_enabled', {}) or {}
    for crop_name, info in crop_info_map.items():
        is_enabled = enabled_map.get(crop_name, False)
        if not is_enabled:
            result[crop_name] = { 'default_percent': None, 'status': 'n/a' }
            continue
        area_m2 = crop_to_area_m2.get(crop_name, 0.0)
        if area_m2 <= 0:
            result[crop_name] = { 'default_percent': None, 'status': 'n/a' }
            continue
        consumption_kg = crop_to_consumption_kg_per_year.get(crop_name)
        if not isinstance(consumption_kg, (int, float)) or consumption_kg <= 0:
            result[crop_name] = { 'default_percent': None, 'status': 'n/a' }
            continue
        space = info.get('space_m2_per_seed')
        weekly_yield_g = info.get('average_yield_g_per_week')
        yield_days = info.get('yield_period_days')
        if not all(isinstance(x, (int, float)) and x > 0 for x in [space, weekly_yield_g, yield_days]):
            result[crop_name] = { 'default_percent': None, 'status': 'n/a' }
            continue
        plants_per_m2 = 1.0 / float(space)
        # Annual yield per plant (kg/year)
        weeks_per_cycle = float(yield_days) / 7.0
        cycles_per_year = 52.1429 / max(weeks_per_cycle, 1e-6)
        annual_yield_per_plant_kg = (float(weekly_yield_g) / 1000.0) * weeks_per_cycle * cycles_per_year
        annual_yield_per_m2_kg = plants_per_m2 * annual_yield_per_plant_kg
        total_production_kg = annual_yield_per_m2_kg * area_m2
        default_percent = max(0.0, (total_production_kg / float(consumption_kg)) * 100.0)
        result[crop_name] = { 'default_percent': default_percent, 'status': 'computed' }

        # Prefill session default if not set
        if crop_name not in st.session_state.wefe_crop_self_sufficiency or st.session_state.wefe_crop_self_sufficiency.get(crop_name, 0) == 0:
            st.session_state.wefe_crop_self_sufficiency[crop_name] = int(min(100, round(default_percent)))

    return result


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

    # Default-enable crops that appear in crop_distribution in Damango lab
    try:
        lab_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'livinglabs', 'ghana_damango', 'lab.json')
        with open(lab_path, 'r', encoding='utf-8') as lf:
            lab = json.load(lf)
        crops_in_distribution = set()
        for site in lab.get('sites', []):
            for entry in site.get('crop_distribution', []) or []:
                name = entry.get('name')
                if isinstance(name, str) and name and name.lower() != 'unused greenland':
                    if float(entry.get('green_share_percent', 0) or 0) > 0:
                        crops_in_distribution.add(name)
        for name in food_names + non_food_names:
            if name in crops_in_distribution and name not in st.session_state.wefe_crop_enabled:
                st.session_state.wefe_crop_enabled[name] = True
    except Exception:
        pass

    # Compute defaults for self-sufficiency for enabled crops
    defaults_map = calculate_self_sufficiency(crop_info_map)

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
            _render_crop_group("Food crops", food_names, crop_info_map, defaults_map)
            _render_crop_group("Non-food crops", non_food_names, crop_info_map, defaults_map)

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


