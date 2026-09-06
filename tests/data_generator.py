import time
from datetime import datetime
from bson import ObjectId


def _uid():
    return str(int(time.time() * 1000))[-6:]


def land_data(uid=None):
    uid = uid or _uid()
    return {
        'name': f'Test Land {uid}',
        'location': {
            'address': {'street': f'{uid} Main St', 'city': 'TestCity', 'state': '', 'postal_code': '', 'country': ''},
            'city': 'TestCity',
            'center_coordinate': {'latitude': 31.12, 'longitude': -7.56},
            'altitude': {'minimum': 450.0, 'maximum': 520.0},
        },
        'metadata': {
            'established_date': '2024-01-15', 'last_updated': '',
            'status': 'active', 'notes': f'Created by test {uid}', 'version': 1
        },
        'farms': [],
        'created_at': datetime.now(),
        'last_updated_at': None,
    }


def farm_data(uid=None):
    uid = uid or _uid()
    return {
        '_id': str(ObjectId()),
        'farm_name': f'Test Farm {uid}',
        'description': f'Description for farm {uid}',
        'location': {
            'area': {'value': 10.5, 'unit': 'ha'},
            'soil_type': 'loam',
            'topography': 'flat',
            'climate_zone': 'mediterranean'
        },
        'boundary': {'type': 'Polygon', 'coordinates': []},
        'irrigation_system': {'type': 'drip', 'source': 'well', 'capacity_lph': 5000, 'notes': ''},
        'legal': {'registration_number': '', 'lease_status': 'owned', 'lease_expiry': '', 'documents': ''},
        'photos': [],
        'metadata': {'created_date': '', 'last_updated': '', 'status': 'active', 'notes': f'Created by test {uid}', 'version': 1},
        'statistics': {'total_sectors': 0, 'total_zones': 0, 'total_rows': 0, 'total_trees': 0, 'cultivated_area': 0},
        'sectors': [],
    }


def sector_data(uid=None):
    uid = uid or _uid()
    return {
        '_id': str(ObjectId()),
        'sector_id': f'S{uid}',
        'sector_number': 1,
        'name': f'Test Sector {uid}',
        'description': f'Description for sector {uid}',
        'location': {
            'area': {'value': 25.5, 'unit': 'ha'},
            'soil_type': 'loam',
            'slope': 'gentle',
            'irrigation_type': 'drip',
        },
        'boundary': {'type': 'Polygon', 'coordinates': []},
        'metadata': {'created_date': '', 'last_updated': '', 'status': 'active', 'notes': f'Created by test {uid}', 'version': 1},
        'statistics': {'total_zones': 0, 'total_rows': 0, 'total_trees': 0},
        'zones': [],
    }


def zone_data(uid=None):
    uid = uid or _uid()
    return {
        '_id': str(ObjectId()),
        'zone_id': f'Z{uid}',
        'zone_number': f'Z01',
        'name': f'Test Zone {uid}',
        'description': f'Description for zone {uid}',
        'location': {
            'area': {'value': 5.0, 'unit': 'ha'},
            'row_spacing': {'value': 12, 'unit': 'feet'},
            'tree_spacing': {'value': 15, 'unit': 'feet'},
            'orientation': 'N-S',
        },
        'boundary': {'type': 'Polygon', 'coordinates': []},
        'crop_info': {
            'current_crop': 'Olives',
            'variety': 'Arbequina',
            'planting_date': '2024-03-01',
            'root_stock': 'Olea-europaea',
            'pollinators': ['Coratina', 'Leccino'],
        },
        'soil_characteristics': {
            'type': 'clay_loam',
            'ph': 7.2,
            'organic_matter': '2.5%',
            'drainage': 'well-drained',
        },
        'statistics': {
            'total_rows': 20, 'total_trees': 400,
            'trees_per_acre': 80, 'active_trees': 390,
            'dead_trees': 10, 'replacement_rate': '2.5%',
        },
        'maintenance': {
            'last_pruned': '2024-06-01', 'last_fertilized': '2024-04-15',
            'last_irrigated': '2024-07-01', 'next_maintenance': '2024-09-01',
            'maintenance_notes': 'Regular schedule',
        },
        'metadata': {
            'created_date': '2024-01-20', 'last_updated': '',
            'status': 'active', 'notes': f'Created by test {uid}',
            'zone_manager': 'Test Manager',
        },
        'rows': [],
    }
