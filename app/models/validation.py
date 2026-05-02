from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from bson import ObjectId

class LandModel(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    soil_type: str = Field(default='loam', pattern='^(sandy|clay|loam|silt)$')
    area: float = Field(..., ge=0)
    boundaries: Optional[str] = None
    
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

class SectorModel(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    land_id: str = Field(...)
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Sector name cannot be empty')
        return v.strip()
    
    @staticmethod
    def check_duplicate(db, name, land_id=None, exclude_id=None):
        query = {'name': name}
        if land_id:
            query['land_id'] = ObjectId(land_id)
        if exclude_id:
            query['_id'] = {'$ne': ObjectId(exclude_id)}
        if db.sectors.find_one(query):
            raise ValueError(f"Sector with name '{name}' already exists")

class ZoneModel(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    sector_id: str = Field(...)
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Zone name cannot be empty')
        return v.strip()
    
    @staticmethod
    def check_duplicate(db, name, sector_id=None, exclude_id=None):
        query = {'name': name}
        if sector_id:
            query['sector_id'] = ObjectId(sector_id)
        if exclude_id:
            query['_id'] = {'$ne': ObjectId(exclude_id)}
        if db.zones.find_one(query):
            raise ValueError(f"Zone with name '{name}' already exists")

class RowModel(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    zone_id: str = Field(...)
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Row name cannot be empty')
        return v.strip()
    
    @staticmethod
    def check_duplicate(db, name, zone_id=None, exclude_id=None):
        query = {'name': name}
        if zone_id:
            query['zone_id'] = ObjectId(zone_id)
        if exclude_id:
            query['_id'] = {'$ne': ObjectId(exclude_id)}
        if db.rows.find_one(query):
            raise ValueError(f"Row with name '{name}' already exists")

class TreeModel(BaseModel):
    name: str = Field(default='Tree', min_length=1, max_length=100)
    row_id: str = Field(...)
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            return 'Tree'
        return v.strip()
    
    @staticmethod
    def check_duplicate(db, name, row_id=None, exclude_id=None):
        query = {'name': name}
        if row_id:
            query['row_id'] = ObjectId(row_id)
        if exclude_id:
            query['_id'] = {'$ne': ObjectId(exclude_id)}
        if db.trees.find_one(query):
            raise ValueError(f"Tree with name '{name}' already exists")

class ActivityModel(BaseModel):
    type: str = Field(..., pattern='^(irrigating|fertilizing|harvesting|planting|pruning)$')
    notes: Optional[str] = None
    date: Optional[datetime] = None

class UserModel(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4)
    role: str = Field(default='guest', pattern='^(guest|worker|admin|customer)$')
