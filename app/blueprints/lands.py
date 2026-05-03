from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort
from app.database import get_db
from app.utils.logging import log_message
from app.models.validation import LandModel, SectorModel, ZoneModel, RowModel, TreeModel
from bson import ObjectId
from datetime import datetime
import folium

lands_bp = Blueprint('lands', __name__, url_prefix='/lands')
lands_bp.strict_slashes = False

lands_bp = Blueprint('lands', __name__, url_prefix='/lands')
lands_bp.strict_slashes = False

@lands_bp.route('/add', methods=['GET', 'POST'])
def add():
    if 'user_id' not in session or session.get('role') not in ['admin', 'worker']:
        flash('Permission denied', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    
    if request.method == 'POST':
        try:
            land_data = LandModel(
                name=request.form.get('name', ''),
                latitude=float(request.form.get('latitude', 0)),
                longitude=float(request.form.get('longitude', 0)),
                soil_type=request.form.get('soil_type', 'loam'),
                area=float(request.form.get('area', 0)),
                boundaries=request.form.get('boundaries', '')
            )
            LandModel.check_duplicate(db, land_data.name)
            db.lands.insert_one(land_data.dict())
            log_message('info', f"Added land: {land_data.name}", session.get('user_id'), session.get('username'))
            flash('Land added successfully!', 'success')
            return redirect(url_for('lands.index'))
        except Exception as e:
            flash(f'Validation error: {str(e)}', 'danger')
    
    return render_template('lands/add.html')

@lands_bp.route('/<land_id>/edit', methods=['GET', 'POST'])
def edit(land_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    land = db.lands.find_one({'_id': ObjectId(land_id)})
    if not land:
        abort(404)
    
    if request.method == 'POST':
        try:
            land_data = LandModel(
                name=request.form.get('name', ''),
                latitude=float(request.form.get('latitude', 0)),
                longitude=float(request.form.get('longitude', 0)),
                soil_type=request.form.get('soil_type', 'loam'),
                area=float(request.form.get('area', 0)),
                boundaries=request.form.get('boundaries', '')
            )
            LandModel.check_duplicate(db, land_data.name, exclude_id=land_id)
            db.lands.update_one({'_id': ObjectId(land_id)}, {'$set': land_data.dict()})
            log_message('info', f"Updated land: {land_data.name}", session.get('user_id'), session.get('username'))
            flash('Land updated successfully!', 'success')
            return redirect(url_for('lands.detail', land_id=land_id))
        except Exception as e:
            flash(f'Validation error: {str(e)}', 'danger')
    
    land['_id'] = str(land['_id'])
    return render_template('lands/edit.html', land=land)

@lands_bp.route('/<land_id>/add-sector', methods=['GET', 'POST'])
def add_sector(land_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    if request.method == 'POST':
        db = get_db()
        sector_data = {
            'name': request.form.get('name'),
            'land_id': ObjectId(land_id)
        }
        db.sectors.insert_one(sector_data)
        log_message('info', f"Added sector: {sector_data['name']}", session.get('user_id'), session.get('username'))
        flash('Sector added successfully!', 'success')
        return redirect(url_for('lands.detail', land_id=land_id))
    
    return render_template('lands/add_sector.html', land_id=land_id)

@lands_bp.route('/', methods=['GET'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    search = request.args.get('search', '').strip()
    
    query = {}
    if search:
        query['name'] = {'$regex': search, '$options': 'i'}
    
    lands = list(db.lands.find(query))
    
    for land in lands:
        land['_id'] = str(land['_id'])
        m = folium.Map(location=[land.get('latitude', 0), land.get('longitude', 0)], zoom_start=10, height='100px')
        folium.Marker([land.get('latitude', 0), land.get('longitude', 0)], popup=land['name']).add_to(m)
        land['map'] = m._repr_html_()
        land['sector_count'] = db.sectors.count_documents({'land_id': ObjectId(land['_id'])})
    
    return render_template('lands/index.html', lands=lands, search=search)

@lands_bp.route('/<land_id>', methods=['GET', 'POST'])
def detail(land_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    land = db.lands.find_one({'_id': ObjectId(land_id)})
    
    if not land:
        return redirect(url_for('lands.index'))
    
    land['_id'] = str(land['_id'])
    
    if request.method == 'POST' and session.get('role') == 'admin':
        entity_type = request.form.get('entity_type')
        
        if entity_type == 'sector':
            sector_data = {
                'name': request.form.get('name'),
                'land_id': ObjectId(land_id)
            }
            db.sectors.insert_one(sector_data)
            db.activities.insert_one({
                'type': 'planting',
                'notes': f'Added sector {request.form.get("name")} to {land["name"]}',
                'date': datetime.utcnow()
            })
            flash('Sector added successfully!', 'success')
        
        elif entity_type == 'zone':
            zone_data = {
                'name': request.form.get('name'),
                'sector_id': ObjectId(request.form.get('parent_id'))
            }
            db.zones.insert_one(zone_data)
            db.activities.insert_one({
                'type': 'planting',
                'notes': f'Added zone {request.form.get("name")}',
                'date': datetime.utcnow()
            })
            flash('Zone added successfully!', 'success')
        
        elif entity_type == 'row':
            row_data = {
                'name': request.form.get('name'),
                'zone_id': ObjectId(request.form.get('parent_id'))
            }
            db.rows.insert_one(row_data)
            db.activities.insert_one({
                'type': 'planting',
                'notes': f'Added row {request.form.get("name")}',
                'date': datetime.utcnow()
            })
            flash('Row added successfully!', 'success')
        
        elif entity_type == 'tree':
            tree_data = {
                'name': request.form.get('name', 'Tree'),
                'row_id': ObjectId(request.form.get('parent_id'))
            }
            db.trees.insert_one(tree_data)
            db.activities.insert_one({
                'type': 'planting',
                'notes': f'Added tree {request.form.get("name", "Tree")}',
                'date': datetime.utcnow()
            })
            flash('Tree added successfully!', 'success')
        
        return redirect(url_for('lands.detail', land_id=land_id))
    
    m = folium.Map(location=[land.get('latitude', 0), land.get('longitude', 0)], zoom_start=12, height='400px')
    folium.Marker([land.get('latitude', 0), land.get('longitude', 0)], popup=land['name']).add_to(m)
    land['map'] = m._repr_html_()
    
    sectors = list(db.sectors.find({'land_id': ObjectId(land_id)}))
    for sector in sectors:
        sector['_id'] = str(sector['_id'])
        sector['zones'] = list(db.zones.find({'sector_id': ObjectId(sector['_id'])}))
        for zone in sector['zones']:
            zone['_id'] = str(zone['_id'])
            zone['rows'] = list(db.rows.find({'zone_id': ObjectId(zone['_id'])}))
            for row in zone['rows']:
                row['_id'] = str(row['_id'])
                row['trees'] = list(db.trees.find({'row_id': ObjectId(row['_id'])}))
                for tree in row['trees']:
                    tree['_id'] = str(tree['_id'])
    
    return render_template('lands/detail.html', land=land, sectors=sectors)

@lands_bp.route('/<land_id>/delete', methods=['POST'])
def delete(land_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    land = db.lands.find_one({'_id': ObjectId(land_id)})
    if land:
        db.lands.delete_one({'_id': ObjectId(land_id)})
        log_message('warning', f'Deleted land {land["name"]}', session.get('user_id'), session.get('username'))
        flash('Land deleted successfully!', 'success')
    
    return redirect(url_for('lands.index'))
