from datetime import datetime
from bson import ObjectId

ACTIVITY_TYPES = [
    ('land_created', 'Land Created'),
    ('land_updated', 'Land Updated'),
    ('sector_created', 'Sector Created'),
    ('zone_created', 'Zone Created'),
    ('row_created', 'Row Created'),
    ('tree_created', 'Tree Created'),
    ('other', 'Other'),
]

class Activity:
    def __init__(self, activity_type, notes='', date=None, status='completed'):
        self.type = activity_type
        self.notes = notes
        self.date = date or datetime.utcnow()
        self.status = status

    def to_dict(self):
        return {
            'type': self.type,
            'notes': self.notes,
            'date': self.date,
            'status': self.status
        }

    @staticmethod
    def is_valid_type(activity_type):
        return any(at[0] == activity_type for at in ACTIVITY_TYPES)
