#!/usr/bin/env python3
"""Initialize xFarming with sample data"""
from app import create_app
from app.database import get_db
from datetime import datetime

def init_sample_data():
    app = create_app()
    
    with app.app_context():
        db = get_db()
        
        # Clear existing data (optional - comment out to keep existing)
        # db.lands.delete_many({})
        # db.sectors.delete_many({})
        # db.zones.delete_many({})
        # db.rows.delete_many({})
        # db.trees.delete_many({})
        # db.activities.delete_many({})
        
        # Check if we already have data
        if db.lands.count_documents({}) > 0:
            print("Sample data already exists. Skipping...")
            return
        
        # Create a sample land
        land = {
            'name': 'North Farm',
            'latitude': 34.123,
            'longitude': -118.456,
            'soil_type': 'loam',
            'area': 25.5,
            'boundaries': '34.120,-118.450;34.130,-118.460;34.125,-118.470',
            'created_at': datetime.utcnow()
        }
        land_id = db.lands.insert_one(land).inserted_id
        print(f"Created land: {land['name']}")
        
        # Create a sector
        sector = {
            'name': 'Sector A',
            'land_id': land_id
        }
        sector_id = db.sectors.insert_one(sector).inserted_id
        print(f"Created sector: {sector['name']}")
        
        # Create a zone
        zone = {
            'name': 'Zone 1',
            'sector_id': sector_id
        }
        zone_id = db.zones.insert_one(zone).inserted_id
        print(f"Created zone: {zone['name']}")
        
        # Create rows
        for i in range(1, 4):
            row = {
                'name': f'Row {i}',
                'zone_id': zone_id
            }
            row_id = db.rows.insert_one(row).inserted_id
            
            # Add trees to each row
            for j in range(1, 6):
                tree = {
                    'name': f'Tree {i}-{j}',
                    'row_id': row_id
                }
                db.trees.insert_one(tree)
            print(f"Created row with 5 trees: {row['name']}")
        
        # Add sample activities
        activities = [
            {'type': 'planting', 'notes': 'Planted new apple trees in North Farm', 'date': datetime.utcnow()},
            {'type': 'irrigating', 'notes': 'Irrigation cycle completed for Sector A', 'date': datetime.utcnow()},
            {'type': 'fertilizing', 'notes': 'Applied organic fertilizer to Zone 1', 'date': datetime.utcnow()}
        ]
        db.activities.insert_many(activities)
        print(f"Created {len(activities)} sample activities")
        
        print("\nSample data initialized successfully!")

if __name__ == '__main__':
    init_sample_data()
