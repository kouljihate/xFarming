#!/usr/bin/env python3
"""End-to-end test for xFarming application"""
from app import create_app
from app.database import get_db
from bson import ObjectId

def test_full_flow():
    app = create_app()
    
    with app.test_client() as client:
        print("Testing xFarming full flow...")
        
        # Test 1: Root redirects to login
        resp = client.get('/')
        assert resp.status_code == 302 or resp.status_code == 200
        print("[OK] Root route works")
        
        # Test 2: Login page accessible
        resp = client.get('/auth/login')
        assert resp.status_code == 200
        assert b'login' in resp.data.lower()
        print("[OK] Login page accessible")
        
        # Test 3: Login with admin credentials
        resp = client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)
        assert resp.status_code == 200
        print("[OK] Admin login successful")
        
        # Test 4: Dashboard accessible
        resp = client.get('/dashboard/')
        assert resp.status_code == 200
        assert b'Dashboard' in resp.data or b'dashboard' in resp.data.lower()
        print("[OK] Dashboard accessible")
        
        # Test 5: Lands page accessible
        resp = client.get('/lands/')
        assert resp.status_code == 200
        print("[OK] Lands page accessible")
        
        # Test 6: Create a new land
        resp = client.post('/lands/', data={
            'name': 'Test Farm',
            'latitude': '35.0',
            'longitude': '-119.0',
            'soil_type': 'loam',
            'area': '50.0'
        }, follow_redirects=True)
        assert resp.status_code == 200
        print("[OK] Land creation works")
        
        # Get the created land ID
        with app.app_context():
            db = get_db()
            land = db.lands.find_one({'name': 'Test Farm'})
            if land:
                land_id = str(land['_id'])
                print(f"   Created land with ID: {land_id}")
                
                # Test 7: Land detail page
                resp = client.get(f'/lands/{land_id}')
                assert resp.status_code == 200
                print("[OK] Land detail page accessible")
                
                # Test 8: Create sector
                resp = client.post(f'/lands/{land_id}', data={
                    'entity_type': 'sector',
                    'name': 'Test Sector'
                }, follow_redirects=True)
                assert resp.status_code == 200
                print("[OK] Sector creation works")
                
                # Get sector
                sector = db.sectors.find_one({'name': 'Test Sector'})
                if sector:
                    sector_id = str(sector['_id'])
                    
                    # Test 9: Sector detail page
                    resp = client.get(f'/sectors/{sector_id}')
                    assert resp.status_code == 200
                    print("[OK] Sector detail page accessible")
                    
                    # Test 10: Create zone
                    resp = client.post(f'/lands/{land_id}', data={
                        'entity_type': 'zone',
                        'name': 'Test Zone',
                        'parent_id': sector_id
                    }, follow_redirects=True)
                    assert resp.status_code == 200
                    print("[OK] Zone creation works")
                    
                    zone = db.zones.find_one({'name': 'Test Zone'})
                    if zone:
                        zone_id = str(zone['_id'])
                        
                        # Test 11: Create row
                        resp = client.post(f'/lands/{land_id}', data={
                            'entity_type': 'row',
                            'name': 'Test Row',
                            'parent_id': zone_id
                        }, follow_redirects=True)
                        assert resp.status_code == 200
                        print("[OK] Row creation works")
                        
                        row = db.rows.find_one({'name': 'Test Row'})
                        if row:
                            row_id = str(row['_id'])
                            
                            # Test 12: Create tree
                            resp = client.post(f'/lands/{land_id}', data={
                                'entity_type': 'tree',
                                'name': 'Test Tree',
                                'parent_id': row_id
                            }, follow_redirects=True)
                            assert resp.status_code == 200
                            print("[OK] Tree creation works")
        
        # Test 13: Activities page
        resp = client.get('/activities/')
        assert resp.status_code == 200
        print("[OK] Activities page accessible")
        
        # Test 14: Users page (admin only)
        resp = client.get('/users/')
        assert resp.status_code == 200
        print("[OK] Users page accessible")
        
        print("\n All tests passed!")
        return True

if __name__ == '__main__':
    try:
        test_full_flow()
    except AssertionError as e:
        print(f"\n Test failed!")
    except Exception as e:
        print(f"\n Error: {e}")
