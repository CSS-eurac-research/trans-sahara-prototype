import streamlit as st
import pandas as pd
import random
import json
import os
import folium
from streamlit.components.v1 import html as st_html
from src.core.data_loader import get_map_data

def render_intervention_tab():
    """Render the intervention management interface"""
    st.title("Intervention Management")
    sim_result = st.session_state.get("policy_simulation_result")
    if sim_result:
        st.markdown("### Recommended interventions (from policy simulation)")
        selected = sim_result.get('selected_interventions', [])
        if selected:
            df = pd.DataFrame([
                {
                    "Title": iv.get('title'),
                    "CAPEX (USD)": iv.get('capex_usd'),
                    "Contributing indicators": ", ".join(sorted(list(iv.get('indicators', {}).keys())))
                }
                for iv in selected
            ])
            st.dataframe(df, use_container_width=True)

            st.markdown("#### Coverage summary vs. policy targets")
            coverage = sim_result.get('coverage', {})
            unmet = sim_result.get('unmet', {})
            if coverage:
                cov_rows = []
                for k in sorted(coverage.keys()):
                    cov_rows.append({
                        "Indicator": k,
                        "Covered change": round(float(coverage.get(k, 0.0)), 2),
                        "Unmet": round(float(unmet.get(k, 0.0)), 2)
                    })
                cov_df = pd.DataFrame(cov_rows)
                st.dataframe(cov_df, use_container_width=True)

            st.info(f"Total CAPEX (USD): {int(sim_result.get('total_capex_usd', 0)):,}")
        else:
            st.warning("No suitable combination of interventions found to meet targets.")
    else:
        st.caption("Run a policy simulation from the Policy tab to see recommendations here.")

    st.divider()
    st.markdown("### Ghana Living Lab - Damango (static)")

    # Helper to estimate an appropriate Leaflet zoom level from bounds and map size
    def _estimate_zoom(min_lat: float, min_lon: float, max_lat: float, max_lon: float, map_width_px: int = 700, map_height_px: int = 900, tile_size: int = 256) -> int:
        try:
            import math
            lon_delta = max(0.000001, abs(max_lon - min_lon))
            lat1 = max(-85.05112878, min(85.05112878, min_lat))
            lat2 = max(-85.05112878, min(85.05112878, max_lat))
            def _lat_rad(lat):
                return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
            lat_rad_delta = abs(_lat_rad(lat2) - _lat_rad(lat1))
            # World size in pixels at zoom 0 is tile_size; width in radians for mercator is 2*pi
            zoom_x = math.log2((map_width_px * 360.0) / (lon_delta * tile_size))
            zoom_y = math.log2((map_height_px * math.pi) / (lat_rad_delta * tile_size)) if lat_rad_delta > 0 else 22
            z = int(max(0, min(22, math.floor(min(zoom_x, zoom_y)))))
            return z
        except Exception:
            return 9

    # Load Damongo sites grid GeoJSON first so we can compute bounds and zoom
    geojson_path = os.path.join("data", "geo", "damongo_sites.geojson")
    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            damongo_geo = json.load(f)
    except Exception as e:
        damongo_geo = None
        st.warning(f"Could not load Damongo sites: {e}")

    # Derive bounds from polygons
    min_lat = min_lon = None
    max_lat = max_lon = None
    if damongo_geo:
        features = damongo_geo.get("features", []) if isinstance(damongo_geo, dict) else []
        boundary_features = [f for f in features if (f.get("properties", {}) or {}).get("role") == "boundary"]
        site_features = [f for f in features if (f.get("properties", {}) or {}).get("role") == "site"]
        def _collect_points(g):
            gtype = (g or {}).get("type")
            if gtype == "Polygon":
                rings = (g.get("coordinates") or [])
                return [pt for ring in rings for pt in ring]
            if gtype == "MultiPolygon":
                polys = (g.get("coordinates") or [])
                return [pt for poly in polys for ring in poly for pt in ring]
            return []
        all_pts = []
        if site_features:
            for f in site_features:
                all_pts.extend(_collect_points((f or {}).get("geometry", {})))
        if not all_pts and boundary_features:
            all_pts.extend(_collect_points((boundary_features[0] or {}).get("geometry", {})))
        if all_pts:
            lons = [p[0] for p in all_pts]
            lats = [p[1] for p in all_pts]
            min_lon, max_lon = min(lons), max(lons)
            min_lat, max_lat = min(lats), max(lats)

    # Fallback bounds if GeoJSON missing
    if min_lat is None:
        ghana_bounds = {
            "upper_left": {"lat": 11.0, "lon": -3.0},
            "lower_right": {"lat": 10.0, "lon": -2.0},
        }
        min_lat, min_lon = ghana_bounds["lower_right"]["lat"], ghana_bounds["upper_left"]["lon"]
        max_lat, max_lon = ghana_bounds["upper_left"]["lat"], ghana_bounds["lower_right"]["lon"]

    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2
    zoom_level = _estimate_zoom(min_lat, min_lon, max_lat, max_lon)

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_level,
        tiles="cartodbpositron",
        control_scale=True,
        zoom_control=False,
        dragging=False,
        scrollWheelZoom=False,
        doubleClickZoom=False,
        boxZoom=False,
        touchZoom=False,
    )

    # We will add a tight blue frame using computed bounds

    # Load Damongo sites grid GeoJSON
    geojson_path = os.path.join("data", "geo", "damongo_sites.geojson")
    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            damongo_geo = json.load(f)
    except Exception as e:
        damongo_geo = None
        st.warning(f"Could not load Damongo sites: {e}")

    if damongo_geo:
        # Split into boundary and sites to control styles and tooltips
        features = damongo_geo.get("features", []) if isinstance(damongo_geo, dict) else []
        boundary_features = [f for f in features if (f.get("properties", {}) or {}).get("role") == "boundary"]
        site_features = [f for f in features if (f.get("properties", {}) or {}).get("role") == "site"]

        # Draw external blue rectangle using precomputed bounds (no dynamic fit)
        folium.Rectangle(
            bounds=[[max_lat, min_lon], [min_lat, max_lon]],
            color="#1f77b4",
            weight=2,
            fill=False,
        ).add_to(m)

        if site_features:
            # Flatten nested land cover dict into top-level properties for tooltip display
            for f in site_features:
                props = f.get("properties") or {}
                lc = props.get("land_cover_percent") or {}
                for key in ("residential", "mixed", "green", "water"):
                    if key in lc and key not in props:
                        try:
                            props[key] = float(lc.get(key))
                        except Exception:
                            props[key] = lc.get(key)
                f["properties"] = props
            sites_fc = {"type": "FeatureCollection", "features": site_features}
            style_fn = lambda feature: {
                "color": "#2c7fb8",
                "weight": 1,
                "fillColor": "#7fcdbb",
                "fillOpacity": 0.25,
            }
            highlight_fn = lambda feature: {
                "weight": 3,
                "color": "#253494",
                "fillColor": "#41b6c4",
                "fillOpacity": 0.45,
            }
            folium.GeoJson(
                sites_fc,
                name="Damongo Sites",
                style_function=style_fn,
                highlight_function=highlight_fn,
                tooltip=folium.GeoJsonTooltip(
                    fields=["name", "surface_m3", "residential", "mixed", "green", "water"],
                    aliases=["Site", "Surface (m³)", "Residential (%)", "Mixed (%)", "Green (%)", "Water (%)"],
                    sticky=True,
                ),
            ).add_to(m)

    # Place map in a dedicated right column
    left_col, right_col = st.columns([1, 1])
    with right_col:
        st_html(m._repr_html_(), height=900)