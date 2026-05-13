from flask import Blueprint, render_template, session, redirect, url_for, request
from app.database import get_db
from app.utils.logging import log_message, log_func_call
from app.models import Activity
from math import ceil
from datetime import datetime

activities_bp = Blueprint('activities', __name__, url_prefix='/activities')
activities_bp.strict_slashes = False

ACTIVITIES_PER_PAGE = 20

@log_func_call
@activities_bp.route('/add', methods=['GET', 'POST'])
def add():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        db = get_db()
        activity_type = request.form.get('type')
        notes = request.form.get('notes', '')
        
        activity = Activity(activity_type, notes, datetime.now())
        db.activities.insert_one(activity.to_dict())
        return redirect(url_for('activities.index'))
    
    return render_template('activities/add.html')

@log_func_call
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
