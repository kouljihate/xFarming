#!/usr/bin/env python3
"""Clean up old collections that are now embedded in lands"""
from app import create_app
from app.database import get_db

app = create_app()

with app.app_context():
    db = get_db()
    collections = ['sectors', 'zones', 'rows', 'trees']
    for collection in collections:
        if collection in db.list_collection_names():
            db[collection].drop()
            print(f"Dropped collection: {collection}")
    print("Cleanup complete!")
