from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort
from app.database import get_db
from app.utils.logging import log_message
from app.models.validation import ZoneModel, RowModel
from bson import ObjectId
from datetime import datetime

zones_bp = Blueprint('zones', __name__, url_prefix='/zones')
zones_bp.strict_slashes = False

@zones_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    search = request.args.get('search', '').strip()
    
    query = {}
    if search:
        query['name'] = {'$regex': search, '$options': 'i'}
    
    zones = list(db.zones.find(query))
    for zone in zones:
        zone['_id'] = str(zone['_id'])
        zone['sector'] = db.sectors.find_one({'_id': zone['sector_id']})
        zone['row_count'] = db.rows.count_documents({'zone_id': ObjectId(zone['_id'])})
    
    return render_template('zones/index.html', zones=zones, search=search)

@zones_bp.route('/add', methods=['GET', 'POST'])
def add():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    sectors = list(db.sectors.find())
    for sector in sectors:
        sector['_id'] = str(sector['_id'])
    
    if request.method == 'POST':
        try:
            zone_data = ZoneModel(
                name=request.form.get('name', ''),
                sector_id=request.form.get('sector_id')
            )
            ZoneModel.check_duplicate(db, zone_data.name, sector_id=zone_data.sector_id)
            db.zones.insert_one({'name': zone_data.name, 'sector_id': ObjectId(zone_data.sector_id)})
            log_message('info', f"Added zone: {zone_data.name}", session.get('user_id'), session.get('username'))
            flash('Zone added successfully!', 'success')
            return redirect(url_for('zones.index'))
        except Exception as e:
            flash(f'Validation error: {str(e)}', 'danger')
    
    return render_template('zones/add.html', sectors=sectors)

@zones_bp.route('/<zone_id>')
def detail(zone_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    zone = db.zones.find_one({'_id': ObjectId(zone_id)})
    if not zone:
        abort(404)
    
    zone['_id'] = str(zone['_id'])
    sector = db.sectors.find_one({'_id': zone['sector_id']})
    land = db.lands.find_one({'_id': sector['land_id']})
    
    rows = list(db.rows.find({'zone_id': ObjectId(zone_id)}))
    for row in rows:
        row['_id'] = str(row['_id'])
        row['tree_count'] = db.trees.count_documents({'row_id': ObjectId(row['_id'])})
    
    return render_template('zones/detail.html', zone=zone, sector=sector, land=land, rows=rows)

@zones_bp.route('/<zone_id>/edit', methods=['GET', 'POST'])
def edit(zone_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    zone = db.zones.find_one({'_id': ObjectId(zone_id)})
    if not zone:
        abort(404)
    
    if request.method == 'POST':
        try:
            zone_data = ZoneModel(
                name=request.form.get('name', ''),
                sector_id=str(zone['sector_id'])
            )
            ZoneModel.check_duplicate(db, zone_data.name, sector_id=zone_data.sector_id, exclude_id=zone_id)
            db.zones.update_one({'_id': ObjectId(zone_id)}, {'$set': {'name': zone_data.name}})
            log_message('info', f"Updated zone: {zone_data.name}", session.get('user_id'), session.get('username'))
            flash('Zone updated successfully!', 'success')
            return redirect(url_for('zones.detail', zone_id=zone_id))
        except Exception as e:
            flash(f'Validation error: {str(e)}', 'danger')
    
    zone['_id'] = str(zone['_id'])
    return render_template('zones/edit.html', zone=zone)

@zones_bp.route('/<zone_id>/add-row', methods=['GET', 'POST'])
def add_row(zone_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    if request.method == 'POST':
        try:
            row_data = RowModel(
                name=request.form.get('name', ''),
                zone_id=zone_id
            )
            RowModel.check_duplicate(db, row_data.name, zone_id=row_data.zone_id)
            db.rows.insert_one({'name': row_data.name, 'zone_id': ObjectId(row_data.zone_id)})
            log_message('info', f"Added row: {row_data.name}", session.get('user_id'), session.get('username'))
            flash('Row added successfully!', 'success')
            return redirect(url_for('zones.detail', zone_id=zone_id))
        except Exception as e:
            flash(f'Validation error: {str(e)}', 'danger')
    
    return render_template('zones/add_row.html', zone_id=zone_id)

@zones_bp.route('/<zone_id>/delete', methods=['POST'])
def delete(zone_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    zone = db.zones.find_one({'_id': ObjectId(zone_id)})
    if zone:
        sector_id = str(zone['sector_id'])
        db.zones.delete_one({'_id': ObjectId(zone_id)})
        log_message('warning', f'Deleted zone {zone["name"]}', session.get('user_id'), session.get('username'))
        flash('Zone deleted successfully!', 'success')
        return redirect(url_for('sectors.detail', sector_id=sector_id))
    
    return redirect(url_for('lands.index'))
