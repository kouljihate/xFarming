#!/usr/bin/env python3
"""Initialize xFarming with sample data"""
from app import create_app
from app.database import get_db
from datetime import datetime
from bson import ObjectId

def init_sample_data():
    app = create_app()
    
    with app.app_context():
        db = get_db()
        
        # Check if we already have data
        if db.lands.count_documents({}) > 0:
            print("Sample data already exists. Skipping...")
            return
        
        print("Creating sample data...")
        
        # Create lands with nested structure
        lands_data = [
            {
                'name': 'North Farm',
                'latitude': 34.123,
                'longitude': -118.456,
                'soil_type': 'loam',
                'area': 25.5,
                'boundaries': '34.123,-118.456',
                'created_at': datetime.utcnow(),
                'sectors': []
            },
            {
                'name': 'South Orchard',
                'latitude': 33.789,
                'longitude': -118.123,
                'soil_type': 'clay',
                'area': 18.2,
                'boundaries': '33.789,-118.123',
                'created_at': datetime.utcnow(),
                'sectors': []
            },
        ]
        
        for land_data in lands_data:
            # Create 2 sectors per land
            for s in range(1, 3):
                sector = {
                    '_id': str(ObjectId()),
                    'name': f'Sector {chr(64+s)}',
                    'zones': []
                }
                print(f"  Created sector: {sector['name']}")
                
                # Create 2 zones per sector
                for z in range(1, 3):
                    zone = {
                        '_id': str(ObjectId()),
                        'name': f'Zone {z}',
                        'rows': []
                    }
                    
                    # Create 3 rows per zone
                    for r in range(1, 4):
                        row = {
                            '_id': str(ObjectId()),
                            'name': f'Row {r}',
                            'trees': []
                        }
                        
                        # Add 5 trees per row
                        for t in range(1, 6):
                            tree = {
                                '_id': str(ObjectId()),
                                'name': f'Tree {r}-{t}'
                            }
                            row['trees'].append(tree)
                        
                        zone['rows'].append(row)
                    
                    sector['zones'].append(zone)
                
                land_data['sectors'].append(sector)
            
            db.lands.insert_one(land_data)
            print(f"Created land: {land_data['name']}")
        
        # Add sample activities
        activities = [
            {'type': 'planting', 'notes': 'Planted new apple trees in North Farm', 'date': datetime.utcnow()},
            {'type': 'irrigating', 'notes': 'Irrigation cycle completed for Sector A', 'date': datetime.utcnow()},
            {'type': 'fertilizing', 'notes': 'Applied organic fertilizer to Zone 1', 'date': datetime.utcnow()},
            {'type': 'harvesting', 'notes': 'Harvested 500kg of apples from Row 1', 'date': datetime.utcnow()},
            {'type': 'pruning', 'notes': 'Pruned trees in South Orchard', 'date': datetime.utcnow()},
        ]
        db.activities.insert_many(activities)
        print(f"\nCreated {len(activities)} sample activities")
        print("\nSample data initialized successfully!")
        print("Login: admin / admin123")

if __name__ == '__main__':
    init_sample_data()
