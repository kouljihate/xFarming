from datetime import datetime
from bson import ObjectId

class Land:
    def __init__(self, id, name, street, city, latitude, longitude, altitude_min, altitude_max):
        self.id = id
        self.name = name
        self.street = street
        self.city = city
        self.latitude = latitude
        self.longitude = longitude
        self.altitude_min = altitude_min
        self.altitude_max = altitude_max
        self.created_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            '_id': self.id,
            'name': self.name,
            'street': self.street,
            'city': self.city,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'altitude_min': self.altitude_min,
            'altitude_max': self.altitude_max,
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
