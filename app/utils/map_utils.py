import sys
import math
import traceback
import plotly.graph_objects as go
import plotly.offline as pyo
from geopy.geocoders import Nominatim
from geopy.point import Point
from math import floor
import requests

def get_altitude_meters(lat: float, lon: float) -> float | None:
    url = "https://api.open-elevation.com/api/v1/lookup"
    resp = requests.get(url, params={"locations": f"{lat},{lon}"}, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    results = data.get("results", [])
    if not results:
        return None
    return results[0].get("elevation")


def _error_info(e):
    tb = sys.exc_info()[-1]
    return {
        'error': True,
        'message': str(e),
        'function': sys._getframe(1).f_code.co_name,
        'line': tb.tb_lineno if tb else 0,
        'trace': traceback.format_exc()
    }


def build_farms_map(farms, height=500):
    try:
        lats = []
        lngs = []
        texts = []
        custom_data = []

        for farm in farms:
            coords = farm.get('center_coordinate', {})
            if not coords:
                location = farm.get('location', {})
                coords = location.get('center_coordinate') or location.get('coordinates') or {}
            lat = coords.get('latitude')
            lng = coords.get('longitude')

            if lat is None or lng is None:
                continue
            try:
                lat_f = float(lat)
                lng_f = float(lng)
                if not (-90 <= lat_f <= 90) or not (-180 <= lng_f <= 180):
                    continue
                lats.append(lat_f)
                lngs.append(lng_f)
                texts.append(farm.get('farm_name', farm.get('name', 'Unknown')))

                sector_count = len(farm.get('sectors', []))
                custom_data.append(sector_count)
            except (ValueError, TypeError):
                continue

        if not lats:
            return None

        min_lat, max_lat = min(lats), max(lats)
        min_lng, max_lng = min(lngs), max(lngs)
        center_lat = (min_lat + max_lat) / 2
        center_lng = (min_lng + max_lng) / 2
        max_span = max(max_lat - min_lat, max_lng - min_lng)

        zoom = max(3, min(17, int(math.log2(360 / max(max_span, 0.0001)))))

        fig = go.Figure(go.Scattermap(
            lat=lats,
            lon=lngs,
            mode='markers',
            marker=go.scattermap.Marker(
                size=14,
                color='red'
            ),
            text=texts,
            customdata=custom_data,
            hovertemplate='<b>%{text}</b><br>' +
                         'Sectors: %{customdata}<br>' +
                         '<extra></extra>'
        ))

        fig.update_layout(
            map=dict(
                style='satellite-streets',
                center=dict(lat=center_lat, lon=center_lng),
                zoom=zoom
            ),
            margin=dict(t=10, l=10, r=10, b=10),
            height=height
        )

        return pyo.plot(fig, output_type='div', include_plotlyjs='cdn')
    except Exception as e:
        return None


def build_farm_edit_map(farm, height=400):
    try:
        import json

        coords = farm.get('center_coordinate', {})
        if not coords:
            location = farm.get('location', {})
            coords = location.get('center_coordinate') or location.get('coordinates') or {}
        lat = coords.get('latitude')
        lng = coords.get('longitude')

        boundary = farm.get('boundary') or {}
        if isinstance(boundary, str):
            try:
                boundary = json.loads(boundary)
            except Exception:
                boundary = {}

        boundary_coords = boundary.get('coordinates', []) if isinstance(boundary, dict) else []

        location = farm.get('location') or {}
        area_dict = location.get('area') or {}
        area = area_dict.get('value', 0) if isinstance(area_dict, dict) else 0
        area_unit = area_dict.get('unit', 'ha') if isinstance(area_dict, dict) else 'ha'
        soil_type = location.get('soil_type', '')
        topography = location.get('topography', '')
        climate_zone = location.get('climate_zone', '')
        farm_name = farm.get('farm_name', farm.get('name', 'Farm'))

        fig = go.Figure()

        has_boundary = False
        boundary_lats = []
        boundary_lngs = []

        if boundary_coords and len(boundary_coords) > 0:
            ring = boundary_coords[0]
            if len(ring) >= 3:
                boundary_lngs = [p[0] for p in ring]
                boundary_lats = [p[1] for p in ring]
                has_boundary = True

        center_lat = lat
        center_lng = lng

        if has_boundary:
            if center_lat is None:
                center_lat = (min(boundary_lats) + max(boundary_lats)) / 2
            if center_lng is None:
                center_lng = (min(boundary_lngs) + max(boundary_lngs)) / 2

        if has_boundary and center_lat is not None:
            fig.add_trace(go.Scattermap(
                lat=boundary_lats,
                lon=boundary_lngs,
                mode='lines',
                fill='toself',
                fillcolor='rgba(46, 180, 100, 0.15)',
                line=dict(width=2, color='#2eb464'),
                name='Boundary',
                hoverinfo='none'
            ))

        if center_lat is not None and center_lng is not None:
            info_text = (
                f"<b>{farm_name}</b><br>"
                f"Area: {area} {area_unit}<br>"
                f"Soil: {soil_type if soil_type else 'N/A'}<br>"
                f"Topography: {topography if topography else 'N/A'}<br>"
                f"Climate: {climate_zone if climate_zone else 'N/A'}"
            )
            fig.add_trace(go.Scattermap(
                lat=[center_lat],
                lon=[center_lng],
                mode='markers',
                marker=go.scattermap.Marker(
                    size=12,
                    color='#2eb464' if has_boundary else 'red'
                ),
                text=[info_text],
                hoverinfo='text',
                name='Farm'
            ))

        if center_lat is not None:
            fig.update_layout(
                map=dict(
                    style='satellite-streets',
                    center=dict(lat=center_lat, lon=center_lng),
                    zoom=15
                ),
                margin=dict(t=10, l=10, r=10, b=10),
                height=height,
                showlegend=False
            )
            return pyo.plot(fig, output_type='div', include_plotlyjs='cdn')

        return None
    except Exception:
        return None


def decimal_to_dms(value: float, is_lat: bool = True) -> str:
    direction = ""
    if is_lat:
        direction = "N" if value >= 0 else "S"
    else:
        direction = "E" if value >= 0 else "W"

    abs_val = abs(value)
    degrees = floor(abs_val)
    minutes_full = (abs_val - degrees) * 60
    minutes = floor(minutes_full)
    seconds = (minutes_full - minutes) * 60

    return f"{degrees}° {minutes}' {seconds:.2f}\" {direction}"


def latlon_to_dms_and_address(lat: float, lon: float) -> dict:
    lat_dms = decimal_to_dms(lat, is_lat=True)
    lon_dms = decimal_to_dms(lon, is_lat=False)

    geolocator = Nominatim(user_agent="latlon_to_address_app")
    location = geolocator.reverse((lat, lon), exactly_one=True, language="en")

    return {
        "latitude_decimal": lat,
        "longitude_decimal": lon,
        "latitude_dms": lat_dms,
        "longitude_dms": lon_dms,
        "address": location.address if location else "Address not found"
    }
