#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    try:
        from app import create_app
        from app.database import get_db
        from app.translations import t
        print("[OK] All imports successful")
        return True
    except Exception as e:
        print(f"[FAIL] Import error: {e}")
        return False

def test_app_creation():
    try:
        from app import create_app
        app = create_app()
        with app.test_client() as client:
            resp = client.get('/auth/login')
            if resp.status_code == 200:
                print("[OK] App creation and login page accessible")
                return True
        print("[FAIL] Login page not accessible")
        return False
    except Exception as e:
        print(f"[FAIL] App creation error: {e}")
        return False

if __name__ == '__main__':
    print("Testing xFarming application...")
    test_imports()
    test_app_creation()
    print("Testing complete.")
