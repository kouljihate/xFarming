from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from app.database import get_db
from app.utils.logging import get_logs
from bson import ObjectId
from math import ceil

users_bp = Blueprint('users', __name__, url_prefix='/users')
users_bp.strict_slashes = False

@users_bp.route('/')
def index():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('dashboard.index'))
    
    db = get_db()
    users = list(db.users.find())
    for user in users:
        user['_id'] = str(user['_id'])
    return render_template('users/index.html', users=users)

@users_bp.route('/change-role/<user_id>', methods=['POST'])
def change_role(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('dashboard.index'))
    
    new_role = request.form.get('role')
    db = get_db()
    db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'role': new_role}})
    flash('Role updated successfully', 'success')
    return redirect(url_for('users.index'))

@users_bp.route('/delete/<user_id>', methods=['POST'])
def delete(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('dashboard.index'))
    
    db = get_db()
    db.users.delete_one({'_id': ObjectId(user_id)})
    flash('User deleted successfully', 'success')
    return redirect(url_for('users.index'))

@users_bp.route('/logs')
def view_logs():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('dashboard.index'))
    
    page = request.args.get('page', 1, type=int)
    level = request.args.get('level', None)
    
    logs, total = get_logs(page=page, level=level)
    per_page = 50
    pages = ceil(total / per_page)
    
    return render_template('users/logs.html', logs=logs, page=page, pages=pages, level=level)
