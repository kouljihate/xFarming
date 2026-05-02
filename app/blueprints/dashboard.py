from flask import Blueprint, render_template, session, redirect, url_for
from app.database import get_db

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')
dashboard_bp.strict_slashes = False

@dashboard_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    
    stats = {
        'lands': db.lands.count_documents({}),
        'sectors': db.sectors.count_documents({}),
        'zones': db.zones.count_documents({}),
        'rows': db.rows.count_documents({}),
        'trees': db.trees.count_documents({})
    }
    
    recent_activities = list(db.activities.find().sort('date', -1).limit(10))
    
    return render_template('dashboard/index.html', stats=stats, activities=recent_activities, treemap=None)
