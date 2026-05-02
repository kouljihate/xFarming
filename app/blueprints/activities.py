from flask import Blueprint, render_template, session, redirect, url_for, request
from app.database import get_db
from math import ceil

activities_bp = Blueprint('activities', __name__, url_prefix='/activities')
activities_bp.strict_slashes = False

ACTIVITIES_PER_PAGE = 20

@activities_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    page = request.args.get('page', 1, type=int)
    db = get_db()
    
    total = db.activities.count_documents({})
    pages = ceil(total / ACTIVITIES_PER_PAGE)
    
    skip = (page - 1) * ACTIVITIES_PER_PAGE
    activities = list(db.activities.find().sort('date', -1).skip(skip).limit(ACTIVITIES_PER_PAGE))
    
    return render_template('activities/index.html', activities=activities, page=page, pages=pages, total=total)
