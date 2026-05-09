from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from bson import ObjectId

class TreeModel(BaseModel):
    tree_id: str = Field(default='')
    position_in_row: int = Field(default=0)
    tree_number: str = Field(default='')
    qr_code: Optional[str] = None
    rfid_tag: Optional[str] = None
    basic_info: Optional[dict] = Field(default_factory=lambda: {
        'species': '', 'common_name': '', 'scientific_name': '',
        'variety': '', 'rootstock': '', 'clone_id': '', 'source': '',
        'source_certified': False, 'planting_date': '', 'planted_by': '',
        'age_years': 0, 'expected_lifespan_years': 25, 'generation': 1
    })
    location_precise: Optional[dict] = Field(default_factory=lambda: {
        'latitude': 0.0, 'longitude': 0.0, 'altitude_meters': 0,
        'accuracy_cm': 0, 'slope_percentage': 0.0, 'aspect': '',
        'distance_to_next_tree_north_cm': 0, 'distance_to_next_tree_south_cm': 0,
        'distance_to_irrigation_row_m': 0.0
    })
    visits: Optional[List[dict]] = Field(default_factory=list)
    historical_production: Optional[List[dict]] = Field(default_factory=list)
    irigation_record: Optional[List[dict]] = Field(default_factory=list)
    photos: Optional[List[dict]] = Field(default_factory=list)
    notes: Optional[List[dict]] = Field(default_factory=list)
    metadata: Optional[dict] = Field(default_factory=lambda: {
        'created_date': '', 'last_updated': '', 'status': 'active',
        'notes': '', 'version': 1, 'data_quality_score': 0,
        'sync_status': '', 'backup_location': ''
    })
    _id: Optional[str] = None

class RowModel(BaseModel):
    row_number: int = Field(default=1)
    name: str = Field(default='Row')
    description: Optional[str] = None
    position: Optional[dict] = Field(default_factory=lambda: {
        'start_coordinates': {'latitude': 0.0, 'longitude': 0.0},
        'end_coordinates': {'latitude': 0.0, 'longitude': 0.0},
        'length': {'value': 0, 'unit': 'feet'},
        'orientation': ''
    })
    tree_count: Optional[dict] = Field(default_factory=lambda: {
        'total_positions': 0, 'active_trees': 0,
        'empty_positions': 0, 'dead_trees': 0, 'replacement_needed': 0
    })
    maintenance: Optional[dict] = Field(default_factory=lambda: {
        'last_pruned': '', 'last_fertilized': '', 'last_irrigated': '',
        'next_maintenance': '', 'maintenance_notes': ''
    })
    metadata: Optional[dict] = Field(default_factory=lambda: {
        'created_date': '', 'last_updated': '', 'status': 'active', 'notes': ''
    })
    trees: List[TreeModel] = Field(default_factory=list)
    _id: Optional[str] = None

class ZoneModel(BaseModel):
    zone_id: str = Field(default='')
    zone_number: str = Field(default='')
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    location: Optional[dict] = Field(default_factory=lambda: {
        'area': {'value': 0, 'unit': 'acres'},
        'row_spacing': {'value': 0, 'unit': 'feet'},
        'tree_spacing': {'value': 0, 'unit': 'feet'},
        'orientation': ''
    })
    boundary: Optional[dict] = Field(default_factory=lambda: {'type': 'Polygon', 'coordinates': []})
    crop_info: Optional[dict] = Field(default_factory=lambda: {
        'current_crop': '', 'variety': '', 'planting_date': '',
        'rootstock': '', 'pollinizers': []
    })
    soil_characteristics: Optional[dict] = Field(default_factory=lambda: {
        'type': '', 'ph': 0.0, 'organic_matter': '', 'drainage': ''
    })
    statistics: Optional[dict] = Field(default_factory=lambda: {
        'total_rows': 0, 'total_trees': 0, 'trees_per_acre': 0,
        'active_trees': 0, 'dead_trees': 0, 'replacement_rate': ''
    })
    maintenance: Optional[dict] = Field(default_factory=lambda: {
        'last_pruned': '', 'last_fertilized': '', 'last_irrigated': '',
        'next_maintenance': '', 'maintenance_notes': ''
    })
    metadata: Optional[dict] = Field(default_factory=lambda: {
        'created_date': '', 'last_updated': '', 'status': 'active',
        'notes': '', 'zone_manager': ''
    })
    rows: List[RowModel] = Field(default_factory=list)
    _id: Optional[str] = None

class SectorModel(BaseModel):
    sector_id: str = Field(default='')
    sector_number: int = Field(default=1)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    location: Optional[dict] = Field(default_factory=lambda: {
        'area': {'value': 0, 'unit': 'acres'},
        'soil_type': 'loam', 'slope': '', 'irrigation_type': ''
    })
    boundary: Optional[dict] = Field(default_factory=lambda: {'type': 'Polygon', 'coordinates': []})
    metadata: Optional[dict] = Field(default_factory=lambda: {
        'created_date': '', 'last_updated': '', 'status': 'active',
        'notes': '', 'version': 1
    })
    statistics: Optional[dict] = Field(default_factory=lambda: {
        'total_zones': 0, 'total_rows': 0, 'total_trees': 0
    })
    zones: List[ZoneModel] = Field(default_factory=list)
    _id: Optional[str] = None

class LandModel(BaseModel):
    farm_id: str = Field(default='', min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    legal: Optional[dict] = Field(default_factory=lambda: {
        'type': ['Document Administratif', 'Malkiya', 'Titre'], 'deleivered': '', 'date': ''
    })
    owner: Optional[dict] = Field(default_factory=lambda: {
        'party_id': '', 'name': '', 'contact': {'email': '', 'phone': ''}
    })
    location: Optional[dict] = Field(default_factory=lambda: {
        'address': {'street': '', 'city': '', 'state': '', 'postal_code': '', 'country': ''},
        'coordinates': {'latitude': 0.0, 'longitude': 0.0},
        'total_area': {'value': 0.0, 'unit': 'acres'},
        'boundary': {'type': 'Polygon', 'coordinates': []}
    })
    metadata: Optional[dict] = Field(default_factory=lambda: {
        'established_date': '', 'last_updated': '', 'status': 'active'
    })
    farms: List[FarmModel] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    _id: Optional[str] = None
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Land name cannot be empty')
        return v.strip()
    
    class Config:
        str_strip_whitespace = True
    
    @staticmethod
    def check_duplicate(db, name, exclude_id=None):
        query = {'name': name}
        if exclude_id:
            query['_id'] = {'$ne': ObjectId(exclude_id)}
        if db.lands.find_one(query):
            raise ValueError(f"Land with name '{name}' already exists")

class ActivityModel(BaseModel):
    type: str = Field(..., pattern='^(irrigating|fertilizing|harvesting|planting|pruning)$')
    notes: Optional[str] = None
    date: Optional[datetime] = None

class FarmModel(BaseModel):
    farm_id: str = Field(default='')
    farm_number: int = Field(default=1)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    location: Optional[dict] = Field(default_factory=lambda: {
        'area': {'value': 0, 'unit': 'acres'},
        'soil_type': 'loam', 'topography': '', 'climate_zone': ''
    })
    boundary: Optional[dict] = Field(default_factory=lambda: {'type': 'Polygon', 'coordinates': []})
    irrigation_system: Optional[dict] = Field(default_factory=lambda: {
        'type': '', 'source': '', 'capacity_lph': 0, 'notes': ''
    })
    metadata: Optional[dict] = Field(default_factory=lambda: {
        'created_date': '', 'last_updated': '', 'status': 'active', 'notes': '', 'version': 1
    })
    statistics: Optional[dict] = Field(default_factory=lambda: {
        'total_sectors': 0, 'total_zones': 0, 'total_rows': 0, 'total_trees': 0, 'cultivated_area': 0
    })
    sectors: List['SectorModel'] = Field(default_factory=list)
    _id: Optional[str] = None


class VisitModel(BaseModel):
    visit_id: str = Field(default='')
    tree_id: Optional[str] = None
    visit_date: str = Field(default='')
    visit_type: str = Field(default='inspection')
    inspector: Optional[str] = None
    status: str = Field(default='pending')
    findings: Optional[dict] = Field(default_factory=lambda: {
        'health_status': '', 'pests': '', 'diseases': '', 'notes': ''
    })
    actions_taken: Optional[List[dict]] = Field(default_factory=list)
    next_visit: Optional[str] = None
    metadata: Optional[dict] = Field(default_factory=lambda: {
        'created_date': '', 'last_updated': '', 'version': 1
    })
    _id: Optional[str] = None


class UserModel(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4)
    role: str = Field(default='guest', pattern='^(guest|worker|admin|customer)$')
