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
    return results[0].get("elevation")  # meters


def _error_info(e):
    tb = sys.exc_info()[-1]
    return {
        'error': True,
        'message': str(e),
        'function': sys._getframe(1).f_code.co_name,
        'line': tb.tb_lineno if tb else 0,
        'trace': traceback.format_exc()
    }


def build_lands_map(lands, height=500):
    try:
        lats = []
        lngs = []
        texts = []
        custom_data = []

        for land in lands:
            location = land.get('location', {})
            coordinates = (location.get('center_coordinate')
                           or location.get('coordinates')
                           or {})
            lat = coordinates.get('latitude')
            lng = coordinates.get('longitude')

            if lat is None or lng is None:
                continue
            try:
                lat_f = float(lat)
                lng_f = float(lng)
                if not (-90 <= lat_f <= 90) or not (-180 <= lng_f <= 180):
                    continue
                lats.append(lat_f)
                lngs.append(lng_f)
                texts.append(land.get('name', 'Unknown'))

                sector_count = len(land.get('sectors', []))

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


def build_land_detail_map(land, height=400):
    try:
        location = land.get('location', {})
        coordinates = (location.get('center_coordinate')
                       or location.get('coordinates')
                       or {})
        lat = coordinates.get('latitude')
        lng = coordinates.get('longitude')

        if lat is None or lng is None:
            return None
        try:
            lat_f = float(lat)
            lng_f = float(lng)
            if not (-90 <= lat_f <= 90) or not (-180 <= lng_f <= 180):
                return None
        except (ValueError, TypeError):
            return None

        fig = go.Figure(go.Scattermap(
            lat=[lat_f],
            lon=[lng_f],
            mode='markers',
            marker=go.scattermap.Marker(
                size=14,
                color='red'
            ),
            text=[land.get('name', 'Unknown')],
            hovertemplate='<b>%{text}</b><br><extra></extra>'
        ))

        fig.update_layout(
            map=dict(
                style='satellite-streets',
                center=dict(lat=lat_f, lon=lng_f),
                zoom=15
            ),
            margin=dict(t=10, l=10, r=10, b=10),
            height=height
        )

        return pyo.plot(fig, output_type='div', include_plotlyjs='cdn')
    except Exception as e:
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
    # WGS84 is the default coordinate reference used by GPS lat/lon
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
