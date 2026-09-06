import sys
import traceback
from pymongo import MongoClient
from bson import ObjectId
from flask import current_app


def _error_info(e):
    tb = sys.exc_info()[-1]
    return {
        'error': True,
        'message': str(e),
        'function': sys._getframe(1).f_code.co_name,
        'line': tb.tb_lineno if tb else 0,
        'trace': traceback.format_exc()
    }


def get_db():
    try:
        client = MongoClient(current_app.config['MONGO_URI'])
        return client.get_database()
    except Exception as e:
        return _error_info(e)


def find_doc(collection, doc_id):
    try:
        doc = collection.find_one({'_id': ObjectId(doc_id)})
        if doc:
            return doc
    except Exception:
        pass
    return collection.find_one({'_id': doc_id})


def init_db():
    try:
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            return db
        if 'users' not in db.list_collection_names():
            db.users.insert_one({
                'username': 'admin',
                'password': 'admin123',
                'role': 'admin'
            })
    except Exception as e:
        return _error_info(e)
