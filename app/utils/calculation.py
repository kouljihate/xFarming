import math
import re
import json


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
    
    area = calculate_area(coords)
    perimeter = calculate_perimeter(coords)
    
    geojson = {
        'type': 'Polygon',
        'coordinates': [coords]
    }
    
    return {
        'area': round(area, 2),
        'perimeter': round(perimeter, 2),
        'geojson': json.dumps(geojson)
    }