import sys
import traceback
from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from app.database import get_db
from app.utils.logging import get_logs, log_message, log_func_call
from bson import ObjectId
from math import ceil

users_bp = Blueprint('users', __name__, url_prefix='/users')
users_bp.strict_slashes = False


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
@users_bp.route('/')
def index():
    try:
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('dashboard.index'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return render_template('users/index.html', users=[])
        users = list(db.users.find())
        for user in users:
            user['_id'] = str(user['_id'])
        return render_template('users/index.html', users=users)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"users.index() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error loading users: {err["message"]}', 'danger')
        return render_template('users/index.html', users=[])


@log_func_call
@users_bp.route('/change-role/<user_id>', methods=['POST'])
def change_role(user_id):
    try:
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('dashboard.index'))
        
        new_role = request.form.get('role')
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('users.index'))
        db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'role': new_role}})
        flash('Role updated successfully', 'success')
        return redirect(url_for('users.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"change_role() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error changing role: {err["message"]}', 'danger')
        return redirect(url_for('users.index'))


@log_func_call
@users_bp.route('/delete/<user_id>', methods=['POST'])
def delete(user_id):
    try:
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('dashboard.index'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('users.index'))
        db.users.delete_one({'_id': ObjectId(user_id)})
        flash('User deleted successfully', 'success')
        return redirect(url_for('users.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"users.delete() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error deleting user: {err["message"]}', 'danger')
        return redirect(url_for('users.index'))


@log_func_call
@users_bp.route('/logs')
def view_logs():
    try:
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('dashboard.index'))
        
        page = request.args.get('page', 1, type=int)
        level = request.args.get('level', None)
        
        logs, total = get_logs(page=page, level=level)
        per_page = 50
        pages = ceil(total / per_page)
        
        return render_template('users/logs.html', logs=logs, page=page, pages=pages, level=level)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"view_logs() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error loading logs: {err["message"]}', 'danger')
        return redirect(url_for('dashboard.index'))
