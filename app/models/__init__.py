from datetime import datetime
from bson import ObjectId

class Land:
    def __init__(self, name, latitude, longitude, soil_type, area, boundaries, sectors=None):
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.soil_type = soil_type
        self.area = area
        self.boundaries = boundaries
        self.sectors = sectors or []
        self.created_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            'name': self.name,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'soil_type': self.soil_type,
            'area': self.area,
            'boundaries': self.boundaries,
            'sectors': self.sectors,
            'created_at': self.created_at
        }

class Activity:
    def __init__(self, activity_type, notes='', date=None):
        self.type = activity_type
        self.notes = notes
        self.date = date or datetime.utcnow()
    
    def to_dict(self):
        return {
            'type': self.type,
            'notes': self.notes,
            'date': self.date
        }
