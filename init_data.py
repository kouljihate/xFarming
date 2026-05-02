#!/usr/bin/env python3
"""Initialize xFarming with sample data"""
from app import create_app
from app.database import get_db
from datetime import datetime

def init_sample_data():
    app = create_app()
    
    with app.app_context():
        db = get_db()
        
        # Check if we already have data
        if db.lands.count_documents({}) > 0:
            print("Sample data already exists. Skipping...")
            return
        
        print("Creating sample data...")
        
        # Create lands
        lands_data = [
            {'name': 'North Farm', 'latitude': 34.123, 'longitude': -118.456, 'soil_type': 'loam', 'area': 25.5},
            {'name': 'South Orchard', 'latitude': 33.789, 'longitude': -118.123, 'soil_type': 'clay', 'area': 18.2},
        ]
        
        for land_data in lands_data:
            land_data['boundaries'] = f"{land_data['latitude']},{land_data['longitude']}"
            land_data['created_at'] = datetime.utcnow()
            land_id = db.lands.insert_one(land_data).inserted_id
            print(f"Created land: {land_data['name']}")
            
            # Create 2 sectors per land
            for s in range(1, 3):
                sector = {
                    'name': f'Sector {chr(64+s)}',
                    'land_id': land_id
                }
                sector_id = db.sectors.insert_one(sector).inserted_id
                print(f"  Created sector: {sector['name']}")
                
                # Create 2 zones per sector
                for z in range(1, 3):
                    zone = {
                        'name': f'Zone {z}',
                        'sector_id': sector_id
                    }
                    zone_id = db.zones.insert_one(zone).inserted_id
                    
                    # Create 3 rows per zone
                    for r in range(1, 4):
                        row = {
                            'name': f'Row {r}',
                            'zone_id': zone_id
                        }
                        row_id = db.rows.insert_one(row).inserted_id
                        
                        # Add 5 trees per row
                        for t in range(1, 6):
                            tree = {
                                'name': f'Tree {r}-{t}',
                                'row_id': row_id
                            }
                            db.trees.insert_one(tree)
        
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
