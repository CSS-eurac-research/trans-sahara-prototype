import json
from typing import Any, Dict, List, Tuple
import folium



def collect_points_from_geometry(geom: Dict[str, Any]) -> List[List[float]]:
    gtype = (geom or {}).get("type")
    if gtype == "Polygon":
        rings = (geom.get("coordinates") or [])
        return [pt for ring in rings for pt in ring]
    if gtype == "MultiPolygon":
        polys = (geom.get("coordinates") or [])
        return [pt for poly in polys for ring in poly for pt in ring]
    return []


def get_bounds_from_features(features: List[Dict[str, Any]]) -> Tuple[float, float, float, float] | None:
    pts: List[List[float]] = []
    for f in features or []:
        geom = (f or {}).get("geometry", {})
        pts.extend(collect_points_from_geometry(geom))
    if not pts:
        return None
    lons = [p[0] for p in pts]
    lats = [p[1] for p in pts]
    return (min(lats), min(lons), max(lats), max(lons))


def estimate_leaflet_zoom(min_lat: float, min_lon: float, max_lat: float, max_lon: float,
                          map_width_px: int = 700, map_height_px: int = 900, tile_size: int = 256) -> int:
    try:
        import math
        lon_delta = max(0.000001, abs(max_lon - min_lon))
        lat1 = max(-85.05112878, min(85.05112878, min_lat))
        lat2 = max(-85.05112878, min(85.05112878, max_lat))
        def _lat_rad(lat: float) -> float:
            return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
        lat_rad_delta = abs(_lat_rad(lat2) - _lat_rad(lat1))
        zoom_x = math.log2((map_width_px * 360.0) / (lon_delta * tile_size))
        zoom_y = math.log2((map_height_px * math.pi) / (lat_rad_delta * tile_size)) if lat_rad_delta > 0 else 22
        return int(max(0, min(22, math.floor(min(zoom_x, zoom_y)))))
    except Exception:
        return 9



def build_damongo_sites_map(geojson: Dict[str, Any] | None) -> Tuple[Any, Tuple[float, float, float, float]]:
    """Create a Folium map for Damongo sites and return it along with (min_lat, min_lon, max_lat, max_lon)."""

    min_lat = max_lat = min_lon = max_lon = None

    features: List[Dict[str, Any]] = []
    if isinstance(geojson, dict):
        features = geojson.get("features", [])

    boundary_features = [f for f in features if (f.get("properties", {}) or {}).get("role") == "boundary"]
    site_features = [f for f in features if (f.get("properties", {}) or {}).get("role") == "site"]

    all_pts: List[List[float]] = []
    if site_features:
        for f in site_features:
            all_pts.extend(collect_points_from_geometry((f or {}).get("geometry", {})))
    if not all_pts and boundary_features:
        all_pts.extend(collect_points_from_geometry((boundary_features[0] or {}).get("geometry", {})))

    if all_pts:
        lons = [p[0] for p in all_pts]
        lats = [p[1] for p in all_pts]
        min_lon, max_lon = min(lons), max(lons)
        min_lat, max_lat = min(lats), max(lats)
    else:
        ghana_bounds = {
            "upper_left": {"lat": 11.0, "lon": -3.0},
            "lower_right": {"lat": 10.0, "lon": -2.0},
        }
        min_lat, min_lon = ghana_bounds["lower_right"]["lat"], ghana_bounds["upper_left"]["lon"]
        max_lat, max_lon = ghana_bounds["upper_left"]["lat"], ghana_bounds["lower_right"]["lon"]

    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2
    zoom_level = estimate_leaflet_zoom(min_lat, min_lon, max_lat, max_lon)

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

    # Draw bbox rectangle
    folium.Rectangle(
        bounds=[[max_lat, min_lon], [min_lat, max_lon]],
        color="#1f77b4",
        weight=2,
        fill=False,
    ).add_to(m)

    # Normalize properties and add sites layer
    if site_features:
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

        def _style_fn(_feature: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "color": "#2c7fb8",
                "weight": 1,
                "fillColor": "#7fcdbb",
                "fillOpacity": 0.25,
            }

        def _highlight_fn(_feature: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "weight": 3,
                "color": "#253494",
                "fillColor": "#41b6c4",
                "fillOpacity": 0.45,
            }

        folium.GeoJson(
            sites_fc,
            name="Damongo Sites",
            style_function=_style_fn,
            highlight_function=_highlight_fn,
            tooltip=folium.GeoJsonTooltip(
                fields=["name", "surface_m3", "residential", "mixed", "green", "water"],
                aliases=["Site", "Surface (m³)", "Residential (%)", "Mixed (%)", "Green (%)", "Water (%)"],
                sticky=True,
            ),
        ).add_to(m)

    return m, (min_lat, min_lon, max_lat, max_lon)
