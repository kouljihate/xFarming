import math
import re
import json
from pyproj import Geod
from shapely.geometry import Polygon

def calculate_polygon_metrics(
    coords: list[tuple[float, float]],
    ellps: str = "WGS84",
) -> dict:
    """
    Calculate the geodesic area and perimeter of a polygon.

    Args:
        coords : List of (latitude, longitude) tuples in decimal degrees.
                 The polygon is auto-closed if the first and last point differ.
        ellps  : Reference ellipsoid (default: "WGS84").

    Returns:
        dict with keys:
            area_m2       – area in square metres
            area_ha       – area in hectares
            area_acres    – area in acres
            perimeter_m   – perimeter in metres
            perimeter_km  – perimeter in kilometres
            num_vertices  – number of unique vertices
    """
    if len(coords) < 3:
        raise ValueError("A polygon requires at least 3 coordinate points.")

    # Auto-close the polygon if needed
    if coords[0] != coords[-1]:
        coords = coords + [coords[0]]

    lons = [c[1] for c in coords]
    lats = [c[0] for c in coords]

    geod = Geod(ellps=ellps)

    # --- Area ---
    poly = Polygon(zip(lons, lats))
    raw_area, _ = geod.geometry_area_perimeter(poly)
    area_m2 = abs(raw_area)

    # --- Perimeter ---
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
        "num_vertices": len(coords) - 1,  # exclude closing point
    }



def calculate_distance(p1, p2):
    return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)


def calculate_perimeter(coordinates):
    if not coordinates or len(coordinates) < 2:
        return 0.0
    
    perimeter = 0.0
    for i in range(len(coordinates) - 1):
        perimeter += calculate_distance(coordinates[i], coordinates[i + 1])
    
    if len(coordinates) > 2:
        perimeter += calculate_distance(coordinates[-1], coordinates[0])
    
    return perimeter


def calculate_area(coordinates):
    print("calculate_area() called - Coordinates: ", len(coordinates))
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
    except Exception:
        return None


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
        perimeter = calculate_perimeter(ring)
        
        return {
            'area': round(area, 2),
            'perimeter': round(perimeter, 2)
        }
    except Exception as e:
        return {'area': 0.0, 'perimeter': 0.0, 'error': str(e)}


def convert_and_calculate(coordinates_str):
    coords = parse_simple_coordinates(coordinates_str)
    
    if not coords:
        return {'error': 'Invalid coordinate format. Use: [(x, y), (x, y), ...]'}
    
    metrics = calculate_polygon_metrics(coords)
    
    
    # metrics = calculate_polygon_metrics(coords)

    # area = calculate_area(coords)
    # perimeter = calculate_perimeter(coords)
    
    geojson = {
        'type': 'Polygon',
        'coordinates': [coords]
    }
    
    return {
        'area': metrics['area_ha'],
        'perimeter': metrics['perimeter_m'],
        'geojson': json.dumps(geojson)
    }