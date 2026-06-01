import sys
import traceback
from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from app.database import get_db
from app.utils.logging import log_message, log_func_call
from app.models import Activity
from math import ceil
from datetime import datetime

activities_bp = Blueprint('activities', __name__, url_prefix='/activities')
activities_bp.strict_slashes = False

ACTIVITIES_PER_PAGE = 20


def _error_info(e):
    tb = sys.exc_info()[-1]
    return {
        'error': True,
        'message': str(e),
        'function': sys._getframe(1).f_code.co_name,
        'line': tb.tb_lineno if tb else 0,
        'trace': traceback.format_exc()
    }


@log_func_call
@activities_bp.route('/add', methods=['GET', 'POST'])
def add():
    try:
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        
        if request.method == 'POST':
            db = get_db()
            if isinstance(db, dict) and db.get('error'):
                flash(f'Database error: {db["message"]}', 'danger')
                return redirect(url_for('activities.index'))
            activity_type = request.form.get('type')
            notes = request.form.get('notes', '')
            
            activity = Activity(activity_type, notes, datetime.now())
            db.activities.insert_one(activity.to_dict())
            return redirect(url_for('activities.index'))
        
        return render_template('activities/add.html')
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"activities.add() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error adding activity: {err["message"]}', 'danger')
        return redirect(url_for('activities.index'))


@log_func_call
@activities_bp.route('/')
def index():
    try:
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        
        page = request.args.get('page', 1, type=int)
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return render_template('activities/index.html', activities=[], page=1, pages=1, total=0)
        
        total = db.activities.count_documents({})
        pages = ceil(total / ACTIVITIES_PER_PAGE)
        
        skip = (page - 1) * ACTIVITIES_PER_PAGE
        activities = list(db.activities.find().sort('date', -1).skip(skip).limit(ACTIVITIES_PER_PAGE))
        
        return render_template('activities/index.html', activities=activities, page=page, pages=pages, total=total)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"activities.index() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error loading activities: {err["message"]}', 'danger')
        return render_template('activities/index.html', activities=[], page=1, pages=1, total=0)
