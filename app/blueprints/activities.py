import sys
import traceback
from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from app.database import get_db
from app.utils.logging import log_message, log_func_call
from app.models import Activity, ACTIVITY_TYPES
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
            status = request.form.get('status', 'completed')
            
            if not activity_type or activity_type not in [at[0] for at in ACTIVITY_TYPES]:
                flash('Invalid activity type selected', 'danger')
                return redirect(url_for('activities.add'))
            
            activity = Activity(activity_type, notes, datetime.now(), status)
            db.activities.insert_one(activity.to_dict())
            flash('Activity added successfully!', 'success')
            return redirect(url_for('activities.index'))
        
        return render_template('activities/add.html', activity_types=ACTIVITY_TYPES)
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
        activity_type_filter = request.args.get('type', '')
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return render_template('activities/index.html', activities=[], page=1, pages=1, total=0, activity_types=ACTIVITY_TYPES)
        
        query = {}
        if activity_type_filter and activity_type_filter in [at[0] for at in ACTIVITY_TYPES]:
            query['type'] = activity_type_filter
        
        total = db.activities.count_documents(query)
        pages = ceil(total / ACTIVITIES_PER_PAGE)
        
        skip = (page - 1) * ACTIVITIES_PER_PAGE
        activities = list(db.activities.find(query).sort('date', -1).skip(skip).limit(ACTIVITIES_PER_PAGE))
        
        return render_template('activities/index.html', 
                           activities=activities, 
                           page=page, 
                           pages=pages, 
                           total=total,
                           activity_types=ACTIVITY_TYPES,
                           activity_type_filter=activity_type_filter)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"activities.index() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error loading activities: {err["message"]}', 'danger')
        return render_template('activities/index.html', activities=[], page=1, pages=1, total=0, activity_types=ACTIVITY_TYPES)