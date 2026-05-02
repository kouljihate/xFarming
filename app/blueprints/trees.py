from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort
from app.database import get_db
from app.utils.logging import log_message
from app.models.validation import TreeModel
from bson import ObjectId
from datetime import datetime

trees_bp = Blueprint('trees', __name__, url_prefix='/trees')
trees_bp.strict_slashes = False

@trees_bp.route('/add', methods=['GET', 'POST'])
def add():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('trees.index'))
    
    db = get_db()
    rows = list(db.rows.find())
    for row in rows:
        row['_id'] = str(row['_id'])
        row['zone'] = db.zones.find_one({'_id': row['zone_id']})
    
    if request.method == 'POST':
        try:
            tree_data = TreeModel(
                name=request.form.get('name', 'Tree'),
                row_id=request.form.get('row_id')
            )
            TreeModel.check_duplicate(db, tree_data.name, row_id=tree_data.row_id)
            db.trees.insert_one({'name': tree_data.name, 'row_id': ObjectId(tree_data.row_id)})
            log_message('info', f"Added tree: {tree_data.name}", session.get('user_id'), session.get('username'))
            flash('Tree added successfully!', 'success')
            return redirect(url_for('trees.index'))
        except Exception as e:
            flash(f'Validation error: {str(e)}', 'danger')
    
    return render_template('trees/add.html', rows=rows)

@trees_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    search = request.args.get('search', '').strip()
    
    query = {}
    if search:
        query['name'] = {'$regex': search, '$options': 'i'}
    
    trees = list(db.trees.find(query))
    for tree in trees:
        tree['_id'] = str(tree['_id'])
        tree['row'] = db.rows.find_one({'_id': tree['row_id']})
    
    return render_template('trees/index.html', trees=trees, search=search)

@trees_bp.route('/<tree_id>')
def detail(tree_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    tree = db.trees.find_one({'_id': ObjectId(tree_id)})
    if not tree:
        abort(404)
    
    tree['_id'] = str(tree['_id'])
    row = db.rows.find_one({'_id': tree['row_id']})
    zone = db.zones.find_one({'_id': row['zone_id']})
    sector = db.sectors.find_one({'_id': zone['sector_id']})
    land = db.lands.find_one({'_id': sector['land_id']})
    
    return render_template('trees/detail.html', tree=tree, row=row, zone=zone, sector=sector, land=land)

@trees_bp.route('/<tree_id>/edit', methods=['GET', 'POST'])
def edit(tree_id):
    if 'user_id' not in session or session.get('role') not in ['admin']:
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    tree = db.trees.find_one({'_id': ObjectId(tree_id)})
    if not tree:
        abort(404)
    
    if request.method == 'POST':
        new_name = request.form.get('name')
        db.trees.update_one({'_id': ObjectId(tree_id)}, {'$set': {'name': new_name}})
        log_message('info', f'Updated tree name to {new_name}', session.get('user_id'), session.get('username'))
        flash('Tree updated successfully!', 'success')
        return redirect(url_for('trees.detail', tree_id=tree_id))
    
    tree['_id'] = str(tree['_id'])
    return render_template('trees/edit.html', tree=tree)

@trees_bp.route('/<tree_id>/delete', methods=['POST'])
def delete(tree_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    tree = db.trees.find_one({'_id': ObjectId(tree_id)})
    if tree:
        row_id = str(tree['row_id'])
        db.trees.delete_one({'_id': ObjectId(tree_id)})
        log_message('warning', f'Deleted tree {tree.get("name", "Unknown")}', session.get('user_id'), session.get('username'))
        flash('Tree deleted successfully!', 'success')
        return redirect(url_for('rows.detail', row_id=row_id))
    
    return redirect(url_for('lands.index'))
