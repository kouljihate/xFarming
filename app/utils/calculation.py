import math
import re
import json
import sys
import traceback
from pyproj import Geod
from shapely.geometry import Polygon


def _error_info(e):
    tb = sys.exc_info()[-1]
    return {
        'error': True,
        'message': str(e),
        'function': sys._getframe(1).f_code.co_name,
        'line': tb.tb_lineno if tb else 0,
        'trace': traceback.format_exc()
    }


def calculate_distance(p1, p2):
    try:
        return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)
    except Exception as e:
        return _error_info(e)


def calculate_perimeter(coordinates):
    try:
        if not coordinates or len(coordinates) < 2:
            return 0.0
        
        perimeter = 0.0
        for i in range(len(coordinates) - 1):
            r = calculate_distance(coordinates[i], coordinates[i + 1])
            if isinstance(r, dict) and r.get('error'):
                return r
            perimeter += r
        
        if len(coordinates) > 2:
            r = calculate_distance(coordinates[-1], coordinates[0])
            if isinstance(r, dict) and r.get('error'):
                return r
            perimeter += r
        
        return perimeter
    except Exception as e:
        return _error_info(e)


def calculate_area(coordinates):
    try:
        if not coordinates or len(coordinates) < 3:
            return 0.0
        
        n = len(coordinates)
        area = 0.0
        
        for i in range(n):
            j = (i + 1) % n
            area += coordinates[i][0] * coordinates[j][1]
            area -= coordinates[j][0] * coordinates[i][1]
        
        area = abs(area) / 2.0
        return area
    except Exception as e:
        return _error_info(e)


def parse_simple_coordinates(input_str):
    try:
        cleaned = input_str.strip().replace(' ', '')
        pattern = r'\((-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)\)'
        matches = re.findall(pattern, cleaned)
        
        if not matches:
            return None
        
        coords = [[float(m[0]), float(m[1])] for m in matches]
        
        if len(coords) < 3:
            return None
        
        return coords
    except Exception as e:
        return _error_info(e)


def calculate_polygon_from_boundary(boundary_json):
    try:
        if isinstance(boundary_json, str):
            data = json.loads(boundary_json)
        else:
            data = boundary_json
        
        if not data or data.get('type') != 'Polygon':
            return {'area': 0.0, 'perimeter': 0.0}
        
        coords = data.get('coordinates', [])
        
        if not coords:
            return {'area': 0.0, 'perimeter': 0.0}
        
        ring = coords[0] if coords else []
        
        if len(ring) < 3:
            return {'area': 0.0, 'perimeter': 0.0}
        
        area = calculate_area(ring)
        if isinstance(area, dict) and area.get('error'):
            return {'area': 0.0, 'perimeter': 0.0, 'error': area['message']}
        perimeter = calculate_perimeter(ring)
        if isinstance(perimeter, dict) and perimeter.get('error'):
            return {'area': 0.0, 'perimeter': 0.0, 'error': perimeter['message']}
        
        return {
            'area': round(area, 2),
            'perimeter': round(perimeter, 2)
        }
    except Exception as e:
        err = _error_info(e)
        return {'area': 0.0, 'perimeter': 0.0, 'error': err['message'], 'line': err['line']}


def convert_and_calculate(coordinates_str):
    try:
        coords = parse_simple_coordinates(coordinates_str)
        
        if isinstance(coords, dict) and coords.get('error'):
            return coords
        
        if not coords:
            return {'error': 'Invalid coordinate format. Use: [(x, y), (x, y), ...]'}
        
        area = calculate_area(coords)
        if isinstance(area, dict) and area.get('error'):
            return area
        perimeter = calculate_perimeter(coords)
        if isinstance(perimeter, dict) and perimeter.get('error'):
            return perimeter
        
        geojson = {
            'type': 'Polygon',
            'coordinates': [coords]
        }
        
        return {
            'area': round(area, 2),
            'perimeter': round(perimeter, 2),
            'geojson': json.dumps(geojson)
        }
    except Exception as e:
        return _error_info(e)


def calculate_centroid(coords) -> dict:
    try:
        if isinstance(coords, str):
            coords = parse_simple_coordinates(coords)
            if isinstance(coords, dict) and coords.get('error'):
                return coords
            if coords is None:
                return _error_info(ValueError("Invalid coordinate format. Use [(lat, lon), (lat, lon), ...]"))
        
        if len(coords) < 3:
            return _error_info(ValueError("A polygon requires at least 3 coordinate points."))

        if coords[0] != coords[-1]:
            coords = coords + [coords[0]]

        poly = Polygon([(lon, lat) for lat, lon in coords])
        if not poly.is_valid:
            poly = poly.buffer(0)

        centroid = poly.centroid
        lat = round(centroid.y, 7)
        lon = round(centroid.x, 7)

        return {
            "latitude":  lat,
            "longitude": lon,
            "maps_url":  f"https://www.google.com/maps?q={lat},{lon}",
        }
    except Exception as e:
        return _error_info(e)


def calculate_polygon_metrics(coords, ellps: str = "WGS84") -> dict:
    try:
        if isinstance(coords, str):
            coords = parse_simple_coordinates(coords)
            if isinstance(coords, dict) and coords.get('error'):
                return coords
            if coords is None:
                return _error_info(ValueError("Invalid coordinate format. Use [(lat, lon), (lat, lon), ...]"))
        
        if len(coords) < 3:
            return _error_info(ValueError("A polygon requires at least 3 coordinate points."))
    
        if coords[0] != coords[-1]:
            coords = coords + [coords[0]]
    
        lons = [c[1] for c in coords]
        lats = [c[0] for c in coords]
    
        geod = Geod(ellps=ellps)
    
        poly = Polygon(zip(lons, lats))
        raw_area, _ = geod.geometry_area_perimeter(poly)
        area_m2 = abs(raw_area)
    
        perimeter_m = 0.0
        for i in range(len(coords) - 1):
            lat1, lon1 = coords[i]
            lat2, lon2 = coords[i + 1]
            _, _, dist = geod.inv(lon1, lat1, lon2, lat2)
            perimeter_m += dist
    
        return {
            "area_m2":      round(area_m2, 4),
            "area_ha":      round(area_m2 / 10_000, 6),
            "area_acres":   round(area_m2 / 4_046.856, 6),
            "perimeter_m":  round(perimeter_m, 4),
            "perimeter_km": round(perimeter_m / 1_000, 6),
            "num_vertices": len(coords) - 1,
        }
    except Exception as e:
        return _error_info(e)
