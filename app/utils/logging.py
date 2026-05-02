from app.database import get_db
from datetime import datetime

def log_message(level, message, user_id=None, username=None):
    """
    Log a message to MongoDB logs collection.
    Levels: 'info', 'warning', 'error'
    """
    if level not in ['info', 'warning', 'error']:
        level = 'info'
    
    db = get_db()
    log_entry = {
        'level': level,
        'message': message,
        'timestamp': datetime.utcnow(),
        'user_id': user_id,
        'username': username
    }
    db.logs.insert_one(log_entry)

def get_logs(page=1, per_page=50, level=None):
    db = get_db()
    query = {}
    if level:
        query['level'] = level
    
    total = db.logs.count_documents(query)
    skip = (page - 1) * per_page
    logs = list(db.logs.find(query).sort('timestamp', -1).skip(skip).limit(per_page))
    
    for log in logs:
        log['_id'] = str(log['_id'])
    
    return logs, total
