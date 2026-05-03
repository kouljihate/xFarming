from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort
from app.database import get_db
from app.utils.logging import log_message
from app.models.validation import RowModel, TreeModel
from bson import ObjectId
from datetime import datetime

rows_bp = Blueprint('rows', __name__, url_prefix='/rows')
rows_bp.strict_slashes = False

@rows_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    search = request.args.get('search', '').strip()
    
    query = {}
    if search:
        query['name'] = {'$regex': search, '$options': 'i'}
    
    rows = list(db.rows.find(query))
    for row in rows:
        row['_id'] = str(row['_id'])
        row['zone'] = db.zones.find_one({'_id': row['zone_id']})
        row['tree_count'] = db.trees.count_documents({'row_id': ObjectId(row['_id'])})
    
    return render_template('rows/index.html', rows=rows, search=search)

@rows_bp.route('/add', methods=['GET', 'POST'])
def add():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('rows.index'))
    
    db = get_db()
    zones = list(db.zones.find())
    for zone in zones:
        zone['_id'] = str(zone['_id'])
        zone['sector'] = db.sectors.find_one({'_id': zone['sector_id']})
    
    if request.method == 'POST':
        try:
            row_data = RowModel(
                name=request.form.get('name', 'Row'),
                zone_id=request.form.get('zone_id')
            )
            RowModel.check_duplicate(db, row_data.name, zone_id=row_data.zone_id)
            db.rows.insert_one({'name': row_data.name, 'zone_id': ObjectId(row_data.zone_id)})
            log_message('info', f"Added row: {row_data.name}", session.get('user_id'), session.get('username'))
            flash('Row added successfully!', 'success')
            return redirect(url_for('rows.index'))
        except Exception as e:
            flash(f'Validation error: {str(e)}', 'danger')
    
    return render_template('rows/add.html', zones=zones)

@rows_bp.route('/<row_id>')
def detail(row_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    row = db.rows.find_one({'_id': ObjectId(row_id)})
    if not row:
        abort(404)
    
    row['_id'] = str(row['_id'])
    zone = db.zones.find_one({'_id': row['zone_id']})
    sector = db.sectors.find_one({'_id': zone['sector_id']})
    land = db.lands.find_one({'_id': sector['land_id']})
    
    trees = list(db.trees.find({'row_id': ObjectId(row_id)}))
    for tree in trees:
        tree['_id'] = str(tree['_id'])
    
    return render_template('rows/detail.html', row=row, zone=zone, sector=sector, land=land, trees=trees)

@rows_bp.route('/<row_id>/edit', methods=['GET', 'POST'])
def edit(row_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('rows.index'))
    
    db = get_db()
    row = db.rows.find_one({'_id': ObjectId(row_id)})
    if not row:
        abort(404)
    
    if request.method == 'POST':
        try:
            row_data = RowModel(
                name=request.form.get('name', ''),
                zone_id=str(row['zone_id'])
            )
            RowModel.check_duplicate(db, row_data.name, zone_id=row_data.zone_id, exclude_id=row_id)
            db.rows.update_one({'_id': ObjectId(row_id)}, {'$set': {'name': row_data.name}})
            log_message('info', f"Updated row: {row_data.name}", session.get('user_id'), session.get('username'))
            flash('Row updated successfully!', 'success')
            return redirect(url_for('rows.detail', row_id=row_id))
        except Exception as e:
            flash(f'Validation error: {str(e)}', 'danger')
    
    row['_id'] = str(row['_id'])
    return render_template('rows/edit.html', row=row)

@rows_bp.route('/<row_id>/add-tree', methods=['GET', 'POST'])
def add_tree(row_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('rows.index'))
    
    if request.method == 'POST':
        try:
            tree_data = TreeModel(
                name=request.form.get('name', 'Tree'),
                row_id=row_id
            )
            TreeModel.check_duplicate(db, tree_data.name, row_id=tree_data.row_id)
            db.trees.insert_one({'name': tree_data.name, 'row_id': ObjectId(tree_data.row_id)})
            log_message('info', f"Added tree: {tree_data.name}", session.get('user_id'), session.get('username'))
            flash('Tree added successfully!', 'success')
            return redirect(url_for('rows.detail', row_id=row_id))
        except Exception as e:
            flash(f'Validation error: {str(e)}', 'danger')
    
    return render_template('rows/add_tree.html', row_id=row_id)

@rows_bp.route('/<row_id>/delete', methods=['POST'])
def delete(row_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    row = db.rows.find_one({'_id': ObjectId(row_id)})
    if row:
        zone_id = str(row['zone_id'])
        db.rows.delete_one({'_id': ObjectId(row_id)})
        log_message('warning', f'Deleted row {row["name"]}', session.get('user_id'), session.get('username'))
        flash('Row deleted successfully!', 'success')
        return redirect(url_for('zones.detail', zone_id=zone_id))
    
    return redirect(url_for('lands.index'))
