import streamlit as st
import json
import os


def _load_strategies() -> dict:
    data_path = os.path.join("data", "agroforestry_strategies.json")
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Failed to load strategies: {e}")
        return {}


def _load_damongo_sites_full() -> list[dict]:
    """Return list of site feature properties for Damango (role == 'site')."""
    geojson_path = os.path.join("data", "geo", "damongo_sites.geojson")
    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            gj = json.load(f)
        sites: list[dict] = []
        for feat in gj.get("features", []):
            props = feat.get("properties", {})
            if props.get("role") == "site":
                sites.append(props)
        return sites
    except Exception as e:
        st.warning(f"Could not load Damongo sites: {e}")
        return []


def _load_damongo_site_names() -> list[str]:
    return sorted([p.get("name") for p in _load_damongo_sites_full() if isinstance(p.get("name"), str)])


def _compute_affected_land_m2(site_props: dict, affected_land_types: list[str]) -> float:
    """Compute affected land for a single site given strategy land types.

    Uses site_props['surface_m3'] as a proxy for area in m² (source dataset label).
    Multiplies by the sum of land_cover_percent for affected types.
    """
    if not site_props:
        return 0.0
    total_area_m2 = float(site_props.get("surface_m3", 0) or 0)
    land_cover_percent = site_props.get("land_cover_percent", {}) or {}
    percent_sum = 0.0
    for land_type in affected_land_types or []:
        try:
            percent_sum += float(land_cover_percent.get(land_type, 0) or 0)
        except Exception:
            continue
    fraction = max(0.0, min(1.0, percent_sum / 100.0))
    return total_area_m2 * fraction


def _render_metrics(title: str, result: dict):
    st.markdown(f"**{title}**")
    row1 = st.columns(3)
    row2 = st.columns(3)

    with row1[0]:
        st.metric(
            label="Affected land",
            value=f"{result.get('affected_m2', 0):,.0f} m²",
        )
    with row1[1]:
        st.metric(
            label="Total cost",
            value=f"${result.get('total_cost_usd', 0):,.0f}",
        )
    with row1[2]:
        st.metric(
            label="Saved water (per year)",
            value=f"{result.get('saved_water_m3_per_year', 0):,.0f} m³",
        )
        

    with row2[0]:
        st.metric(
            label="Saved energy (per year)",
            value=f"{result.get('saved_energy_kwh_per_year', 0):,.0f} kWh",
        )
    with row2[1]:
        st.metric(
            label="Carbon sequestration (per year)",
            value=f"{result.get('carbon_sequestration_kgco2e_per_year', 0):,.0f} kg CO₂e",
        )
    with row2[2]:
        # Spacer or additional metric placeholder
        st.markdown(
            """
            <div style="margin-top:8px;background:#d4edda;color:#155724;border:1px solid #c3e6cb;border-radius:8px;padding:10px 12px;font-weight:700;text-align:center;font-size:30px;">
              SCORE: 
              88.4%
            </div>
            """,
            unsafe_allow_html=True,
        )


def _calculate_productivity_increase_percent(crop_name: str, scope: str) -> float:
    """Placeholder: returns a random productivity increase between 5% and 100%."""
    import random
    return random.uniform(5.0, 100.0)


# ---- Production helpers ----

def _load_lab_and_resources():
    try:
        base = os.path.join("data", "livinglabs", "ghana_damango")
        with open(os.path.join(base, "lab.json"), "r", encoding="utf-8") as lf:
            lab = json.load(lf)
        with open(os.path.join(base, "lab_resources_info.json"), "r", encoding="utf-8") as rf:
            resources = json.load(rf)
        return lab, resources
    except Exception as e:
        st.warning(f"Could not load lab/resources: {e}")
        return None, None


def _load_crop_info_map() -> dict:
    try:
        with open(os.path.join("data", "crops.json"), "r", encoding="utf-8") as cf:
            crops = json.load(cf)
        crop_info_map = {}
        for group in ["food", "non-food"]:
            for c in crops.get(group, []) or []:
                if isinstance(c, dict) and c.get("name"):
                    crop_info_map[c["name"]] = c
        return crop_info_map
    except Exception as e:
        st.warning(f"Could not load crops: {e}")
        return {}


def _compute_crop_area_map(lab: dict, scope_site_name: str | None) -> dict[str, float]:
    """Return map crop_name -> area_m2 allocated (from green area and crop_distribution)."""
    crop_to_area: dict[str, float] = {}
    for site in lab.get("sites", []) or []:
        if scope_site_name and site.get("name") != scope_site_name:
            continue
        total_area_m2 = float(site.get("surface_m3", 0) or 0)
        green_pct = float((site.get("land_cover_percent", {}) or {}).get("green", 0) or 0)
        green_area_m2 = total_area_m2 * max(0.0, min(1.0, green_pct / 100.0))
        for dist in (site.get("crop_distribution") or []):
            name = dist.get("name")
            if not isinstance(name, str) or name.lower() == "unused greenland":
                continue
            share = float(dist.get("green_share_percent", 0) or 0)
            crop_to_area[name] = crop_to_area.get(name, 0.0) + green_area_m2 * max(0.0, min(1.0, share / 100.0))
    return crop_to_area


def _compute_self_sufficiency(crop_name: str, crop_info: dict, area_m2: float, annual_consumption_kg: float, weekly_yield_g: float) -> float | None:
    if area_m2 <= 0 or not isinstance(annual_consumption_kg, (int, float)) or annual_consumption_kg <= 0:
        return None
    space = crop_info.get("space_m2_per_seed")
    yield_days = crop_info.get("yield_period_days")
    if not all(isinstance(x, (int, float)) and x > 0 for x in [space, weekly_yield_g, yield_days]):
        return None
    plants_per_m2 = 1.0 / float(space)
    weeks_per_cycle = float(yield_days) / 7.0
    cycles_per_year = 52.1429 / max(weeks_per_cycle, 1e-6)
    annual_yield_per_plant_kg = (float(weekly_yield_g) / 1000.0) * weeks_per_cycle * cycles_per_year
    annual_yield_per_m2_kg = plants_per_m2 * annual_yield_per_plant_kg
    total_production_kg = annual_yield_per_m2_kg * area_m2
    return max(0.0, (total_production_kg / float(annual_consumption_kg)) * 100.0)


def render_agroforestry_analysis():
    st.title("Agroforestry Analysis")

    # Initialize state for applied strategies
    if "agro_applied_strategies" not in st.session_state:
        st.session_state.agro_applied_strategies = []

    # Load data
    strategies_doc = _load_strategies()
    strategies = strategies_doc.get("strategies", []) if isinstance(strategies_doc, dict) else []
    if not strategies:
        st.info("No strategies found. Please ensure data/agroforestry_strategies.json exists.")
        return

    strategy_name_to_obj = {s.get("name", s.get("key")): s for s in strategies}
    strategy_names = list(strategy_name_to_obj.keys())

    selected_strategy_name = st.selectbox("Select an agroforestry strategy", strategy_names, index=0)
    selected_strategy = strategy_name_to_obj.get(selected_strategy_name, {})

    left, right = st.columns([1, 1])

    with left:
        st.subheader("Strategy details")
        # st.markdown(f"**Name**: {selected_strategy.get('name', '-')}")
        # st.markdown(f"**Key**: `{selected_strategy.get('key', '-')}`")
        st.markdown(f"**Description**: {selected_strategy.get('description', '-')}")

        affected = selected_strategy.get("affected_land_types", [])
        st.markdown("**Affected land types**:")
        if affected:
            st.write(", ".join(affected))
        else:
            st.write("-")

        indicators = selected_strategy.get("impacted_indicators", [])
        st.markdown("**Impacted indicators (IDs)**:")
        if indicators:
            st.code("\n".join(indicators))
        else:
            st.write("-")

        cost = selected_strategy.get("cost_per_sqm_usd", None)
        if isinstance(cost, (int, float)):
            st.markdown(f"**Cost per m² (USD)**: {cost}")
        else:
            st.markdown("**Cost per m² (USD)**: -")

        # Extra fields helpful for analysis
        # st.markdown("**Time horizon (years)**:")
        # th = selected_strategy.get("time_horizon_years", {})
        # st.write({k: th.get(k) for k in ["establishment", "full_benefit"] if k in th})

        # st.markdown("**Maintenance intensity**:")
        st.write(selected_strategy.get("maintenance_intensity", "-"))

        st.markdown("**Expected co-benefits**:")
        cob = selected_strategy.get("expected_co_benefits", [])
        if cob:
            st.write(", ".join(cob))
        else:
            st.write("-")

        st.markdown("**Data assumptions**:")
        st.write(selected_strategy.get("data_assumptions", "-"))

    with right:
        st.subheader("Target area: Ghana Living Lab - Damango")
        sites_props = _load_damongo_sites_full()
        site_names = sorted([p.get("name") for p in sites_props if isinstance(p.get("name"), str)])
        site_options = ["Apply to all sites"] + site_names
        selected_target = st.selectbox("Apply to all sites or a specific site", site_options, index=0)

        # Adjustable assumptions for simple impact estimation
        with st.expander("Assumptions for impact estimation", expanded=False):
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                water_gain_l_per_m2 = st.number_input(
                    "Water saved/infiltration (L per m² per year)", min_value=0.0, max_value=200.0, value=20.0, step=1.0
                )
            with col_b:
                energy_saved_kwh_per_m3 = st.number_input(
                    "Energy saved per m³ (kWh)", min_value=0.0, max_value=5.0, value=0.2, step=0.05
                )
            with col_c:
                carbon_seq_kgco2e_per_m2 = st.number_input(
                    "Carbon sequestration (kg CO₂e per m² per year)", min_value=0.0, max_value=20.0, value=0.5, step=0.1
                )

        # Compute affected land and cost (preview for current selection)
        affected_types = selected_strategy.get("affected_land_types", [])
        unit_cost = float(selected_strategy.get("cost_per_sqm_usd", 0) or 0)

        def compute_for_site(props: dict, water_l_per_m2: float, energy_kwh_per_m3: float, carbon_kgco2e_per_m2: float) -> dict:
            affected_m2 = _compute_affected_land_m2(props, affected_types)
            total_cost = affected_m2 * unit_cost
            saved_water_m3 = (affected_m2 * water_l_per_m2) / 1000.0
            saved_energy_kwh = saved_water_m3 * energy_kwh_per_m3
            carbon_kgco2e = affected_m2 * carbon_kgco2e_per_m2
            return {
                "site": props.get("name", "-"),
                "affected_m2": affected_m2,
                "total_cost_usd": total_cost,
                "saved_water_m3_per_year": saved_water_m3,
                "saved_energy_kwh_per_year": saved_energy_kwh,
                "carbon_sequestration_kgco2e_per_year": carbon_kgco2e,
            }

        if selected_target == "Apply to all sites":
            st.success("The selected strategy will be considered for all Damango sites.")
            results = [compute_for_site(props, water_gain_l_per_m2, energy_saved_kwh_per_m3, carbon_seq_kgco2e_per_m2) for props in sites_props]
            agg = {
                "affected_m2": sum(r["affected_m2"] for r in results),
                "total_cost_usd": sum(r["total_cost_usd"] for r in results),
                "saved_water_m3_per_year": sum(r["saved_water_m3_per_year"] for r in results),
                "saved_energy_kwh_per_year": sum(r["saved_energy_kwh_per_year"] for r in results),
                "carbon_sequestration_kgco2e_per_year": sum(r["carbon_sequestration_kgco2e_per_year"] for r in results),
            }
            _render_metrics("Aggregate impacts (all sites)", agg)
            scope_label = "all sites"
            scope_site_name: str | None = None
        else:
            st.info(f"The selected strategy will be considered for site: {selected_target}")
            site_props = next((p for p in sites_props if p.get("name") == selected_target), None)
            if site_props is None:
                st.warning("Selected site not found in data.")
                scope_label = selected_target
                scope_site_name = None
            else:
                r = compute_for_site(site_props, water_gain_l_per_m2, energy_saved_kwh_per_m3, carbon_seq_kgco2e_per_m2)
                _render_metrics("Impacts (selected site)", r)
                scope_label = selected_target
                scope_site_name = selected_target

        st.divider()
        st.caption("Impacts are based on affected land share within site(s) and simple adjustable coefficients for savings.")

        # Production section based on crops selected in WEFE Analysis
        st.subheader("Production")
        enabled_map = st.session_state.get("wefe_crop_enabled", {}) or {}
        selected_crops = [name for name, enabled in enabled_map.items() if enabled]

        lab, resources = _load_lab_and_resources()
        crop_info_map = _load_crop_info_map()
        if not lab or not resources:
            st.info("Lab resources not available.")
            return
        # Build annual consumption (kg/year)
        consumption_map = {}
        for entry in resources.get("food", []) or []:
            if isinstance(entry, dict) and isinstance(entry.get("annual_consumption"), (int, float)):
                consumption_map[entry.get("name")] = float(entry["annual_consumption"]) * 1000.0
        # Area per crop according to crop_distribution and scope
        crop_area_map = _compute_crop_area_map(lab, scope_site_name)

        if selected_crops:
            import pandas as pd
            rows = []
            for crop in selected_crops:
                increase_pct = _calculate_productivity_increase_percent(str(crop), scope_label)
                info = crop_info_map.get(crop, {})
                area_m2 = float(crop_area_map.get(crop, 0) or 0)
                consumption_kg = consumption_map.get(crop)
                weekly_yield_g = info.get("average_yield_g_per_week")
                # Baseline and new self-sufficiency computed explicitly
                baseline_ss = _compute_self_sufficiency(crop, info, area_m2, consumption_kg, weekly_yield_g)
                new_weekly_yield_g = (weekly_yield_g * (1.0 + increase_pct / 100.0)) if isinstance(weekly_yield_g, (int, float)) else None
                new_ss = _compute_self_sufficiency(crop, info, area_m2, consumption_kg, new_weekly_yield_g)
                rows.append({
                    "Crop": crop,
                    "Increase of productivity (%)": round(increase_pct, 1),
                    "Starting self-sufficiency (%)": round((baseline_ss or 0.0), 1),
                    "New self-sufficiency (%)": round((new_ss or 0.0), 1)
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
            # Apply button to add current configuration to applied strategies list
            if st.button("Apply", type="primary"):
                st.session_state.agro_applied_strategies.append({
                    "strategy_key": selected_strategy.get("key"),
                    "strategy_name": selected_strategy.get("name"),
                    "target": "ALL" if scope_site_name is None else scope_site_name,
                    "affected_types": affected_types,
                    "unit_cost": unit_cost,
                    "assumptions": {
                        "water_gain_l_per_m2": water_gain_l_per_m2,
                        "energy_saved_kwh_per_m3": energy_saved_kwh_per_m3,
                        "carbon_seq_kgco2e_per_m2": carbon_seq_kgco2e_per_m2,
                        "productivity_increase_percent": _calculate_productivity_increase_percent("*", scope_label)
                    }
                })
                st.success("Strategy applied.")
        else:
            st.info("No crops selected in WEFE Analysis.")

    # ---- Applied strategies list and aggregate summary ----
    st.divider()
    st.markdown("""
    <div style="background:#f7f9fb;border:1px solid #e3e8ef;border-radius:10px;padding:12px 14px;margin-top:8px;">
      <div style="font-weight:700;font-size:1.05rem;margin-bottom:6px;">Applied agroforestry strategies</div>
    </div>
    """, unsafe_allow_html=True)
    apps = st.session_state.get("agro_applied_strategies", [])
    if not apps:
        st.caption("No strategies applied yet.")
        return

    # List applied strategies with remove buttons, each in bordered card with spacing
    for idx, app in enumerate(list(apps)):
        with st.container(border=True):
            cols = st.columns([4, 3, 1])
            with cols[0]:
                st.markdown(f"**{app.get('strategy_name','-')}**")
            with cols[1]:
                st.markdown(f"Target: {app.get('target','-')}")
                st.markdown(f"Affected: {', '.join(app.get('affected_types', [])) or '-'}")
            with cols[2]:
                if st.button("✖", key=f"remove_app_{idx}"):
                    st.session_state.agro_applied_strategies.pop(idx)
                    st.experimental_rerun()
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    st.divider()

    # Aggregate impacts across applied strategies
    sites_props_all = _load_damongo_sites_full()

    def aggregate_impacts(applications: list[dict]) -> dict:
        totals = {
            "affected_m2": 0.0,
            "total_cost_usd": 0.0,
            "saved_water_m3_per_year": 0.0,
            "saved_energy_kwh_per_year": 0.0,
            "carbon_sequestration_kgco2e_per_year": 0.0,
        }
        for app in applications:
            aff_types = app.get("affected_types", [])
            unit_cost_local = float(app.get("unit_cost", 0) or 0)
            target = app.get("target")
            assumptions = app.get("assumptions", {})
            water_l_per_m2 = float(assumptions.get("water_gain_l_per_m2", 0) or 0)
            energy_kwh_per_m3 = float(assumptions.get("energy_saved_kwh_per_m3", 0) or 0)
            carbon_kgco2e_per_m2 = float(assumptions.get("carbon_seq_kgco2e_per_m2", 0) or 0)

            def compute(site_props: dict) -> dict:
                total_area_m2 = float(site_props.get("surface_m3", 0) or 0)
                land_cover_percent = site_props.get("land_cover_percent", {}) or {}
                percent_sum = sum(float(land_cover_percent.get(t, 0) or 0) for t in aff_types)
                fraction = max(0.0, min(1.0, percent_sum / 100.0))
                affected_m2 = total_area_m2 * fraction
                total_cost = affected_m2 * unit_cost_local
                saved_water_m3 = (affected_m2 * water_l_per_m2) / 1000.0
                saved_energy_kwh = saved_water_m3 * energy_kwh_per_m3
                carbon_kgco2e = affected_m2 * carbon_kgco2e_per_m2
                return affected_m2, total_cost, saved_water_m3, saved_energy_kwh, carbon_kgco2e

            if target == "ALL":
                sites_iter = sites_props_all
            else:
                sites_iter = [s for s in sites_props_all if s.get("name") == target]
            for sp in sites_iter:
                a, c, w, e, co2 = compute(sp)
                totals["affected_m2"] += a
                totals["total_cost_usd"] += c
                totals["saved_water_m3_per_year"] += w
                totals["saved_energy_kwh_per_year"] += e
                totals["carbon_sequestration_kgco2e_per_year"] += co2
        return totals

    agg_totals = aggregate_impacts(apps)
    _render_metrics("Aggregated impacts (all applied)", agg_totals)

    # Aggregate production using multiplicative productivity increases across applied strategies
    lab, resources = _load_lab_and_resources()
    crop_info_map = _load_crop_info_map()
    if lab and resources:
        consumption_map = {}
        for entry in resources.get("food", []) or []:
            if isinstance(entry, dict) and isinstance(entry.get("annual_consumption"), (int, float)):
                consumption_map[entry.get("name")] = float(entry["annual_consumption"]) * 1000.0
        # Effective multiplier per crop = product over apps of (1 + p/100)
        effective_multiplier = 1.0
        for app in apps:
            p = float(app.get("assumptions", {}).get("productivity_increase_percent", 0) or 0)
            effective_multiplier *= (1.0 + p / 100.0)
        # Use ALL sites area for production aggregate
        crop_area_map_all = _compute_crop_area_map(lab, None)
        enabled_map = st.session_state.get("wefe_crop_enabled", {}) or {}
        selected_crops_all = [name for name, enabled in enabled_map.items() if enabled]
        if selected_crops_all:
            import pandas as pd
            rows = []
            for crop in selected_crops_all:
                info = crop_info_map.get(crop, {})
                area_m2 = float(crop_area_map_all.get(crop, 0) or 0)
                consumption_kg = consumption_map.get(crop)
                weekly_yield_g = info.get("average_yield_g_per_week")
                baseline_ss = _compute_self_sufficiency(crop, info, area_m2, consumption_kg, weekly_yield_g)
                new_weekly_yield_g = (weekly_yield_g * effective_multiplier) if isinstance(weekly_yield_g, (int, float)) else None
                new_ss = _compute_self_sufficiency(crop, info, area_m2, consumption_kg, new_weekly_yield_g)
                rows.append({
                    "Crop": crop,
                    "Effective productivity increase (%)": round((effective_multiplier - 1) * 100.0, 1),
                    "Starting self-sufficiency (%)": round((baseline_ss or 0.0), 1),
                    "New self-sufficiency (%)": round((new_ss or 0.0), 1)
                })
            df_all = pd.DataFrame(rows)
            st.markdown("**Aggregated production (all applied)**")
            st.dataframe(df_all, use_container_width=True, hide_index=True)



