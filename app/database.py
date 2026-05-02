from pymongo import MongoClient
from flask import current_app

def get_db():
    client = MongoClient(current_app.config['MONGO_URI'])
    return client.get_database()

def init_db():
    db = get_db()
    if 'users' not in db.list_collection_names():
        db.users.insert_one({
            'username': 'admin',
            'password': 'admin123',
            'role': 'admin'
        })
