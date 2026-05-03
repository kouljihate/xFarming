from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort
from app.database import get_db
from app.utils.logging import log_message
from app.models.validation import LandModel, SectorModel, ZoneModel, RowModel, TreeModel
from bson import ObjectId
from datetime import datetime
import folium

lands_bp = Blueprint('lands', __name__, url_prefix='/lands')
lands_bp.strict_slashes = False

@lands_bp.route('/add', methods=['POST'])
def add():
    if 'user_id' not in session or session.get('role') not in ['admin', 'worker']:
        flash('Permission denied', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    
    try:
        land_data = LandModel(
            name=request.form.get('name', ''),
            location={
                'coordinates': {
                    'latitude': float(request.form.get('latitude', 0)),
                    'longitude': float(request.form.get('longitude', 0))
                },
                'total_area': {'value': float(request.form.get('area', 0)), 'unit': 'acres'},
                'boundary': {'type': 'Polygon', 'coordinates': []}
            },
            metadata={'established_date': '', 'last_updated': '', 'status': 'active'}
        )
        LandModel.check_duplicate(db, land_data.name)
        land_dict = land_data.model_dump()
        land_dict['sectors'] = []
        db.lands.insert_one(land_dict)
        log_message('info', f"Added land: {land_data.name}", session.get('user_id'), session.get('username'))
        flash('Land added successfully!', 'success')
    except Exception as e:
        flash(f'Validation error: {str(e)}', 'danger')
    
    return redirect(url_for('lands.index'))

@lands_bp.route('/<land_id>/edit', methods=['POST'])
def edit(land_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    land = db.lands.find_one({'_id': ObjectId(land_id)})
    if not land:
        abort(404)
    
    try:
        # Build location dict from form data
        location = land.get('location', {})
        location['coordinates'] = {
            'latitude': float(request.form.get('latitude', 0)),
            'longitude': float(request.form.get('longitude', 0))
        }
        location['total_area'] = {'value': float(request.form.get('area', 0)), 'unit': 'acres'}
        
        land_data = LandModel(
            name=request.form.get('name', ''),
            location=location,
            metadata={'established_date': '', 'last_updated': '', 'status': 'active'}
        )
        LandModel.check_duplicate(db, land_data.name, exclude_id=land_id)
        
        # Update only specific fields
        db.lands.update_one(
            {'_id': ObjectId(land_id)}, 
            {'$set': {'name': land_data.name, 'location': location}}
        )
        log_message('info', f"Updated land: {land_data.name}", session.get('user_id'), session.get('username'))
        flash('Land updated successfully!', 'success')
    except Exception as e:
        flash(f'Validation error: {str(e)}', 'danger')
    
    return redirect(url_for('lands.index'))

@lands_bp.route('/<land_id>/add-sector', methods=['GET', 'POST'])
def add_sector(land_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    if request.method == 'POST':
        db = get_db()
        sector_name = request.form.get('name')
        land = db.lands.find_one({'_id': ObjectId(land_id)})
        if land:
            if 'sectors' not in land:
                land['sectors'] = []
            land['sectors'].append({
                '_id': str(ObjectId()),
                'name': sector_name,
                'zones': []
            })
            db.lands.update_one({'_id': ObjectId(land_id)}, {'$set': {'sectors': land['sectors']}})
            log_message('info', f"Added sector: {sector_name}", session.get('user_id'), session.get('username'))
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
        m = folium.Map(location=[land.get('latitude', 0), land.get('longitude', 0)], zoom_start=10, width='100%', height='200px')
        folium.Marker([land.get('latitude', 0), land.get('longitude', 0)], popup=land['name']).add_to(m)
        land['map'] = m._repr_html_()
        land['sector_count'] = len(land.get('sectors', []))
    
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
        parent_id = request.form.get('parent_id')
        
        if entity_type == 'sector':
            if 'sectors' not in land:
                land['sectors'] = []
            land['sectors'].append({
                '_id': str(ObjectId()),
                'name': request.form.get('name'),
                'zones': []
            })
            db.lands.update_one({'_id': ObjectId(land_id)}, {'$set': {'sectors': land['sectors']}})
            db.activities.insert_one({
                'type': 'planting',
                'notes': f'Added sector {request.form.get("name")} to {land["name"]}',
                'date': datetime.utcnow()
            })
            flash('Sector added successfully!', 'success')
        
        elif entity_type == 'zone':
            for sector in land.get('sectors', []):
                if sector['_id'] == parent_id:
                    if 'zones' not in sector:
                        sector['zones'] = []
                    sector['zones'].append({
                        '_id': str(ObjectId()),
                        'name': request.form.get('name'),
                        'rows': []
                    })
                    break
            db.lands.update_one({'_id': ObjectId(land_id)}, {'$set': {'sectors': land['sectors']}})
            db.activities.insert_one({
                'type': 'planting',
                'notes': f'Added zone {request.form.get("name")}',
                'date': datetime.utcnow()
            })
            flash('Zone added successfully!', 'success')
        
        elif entity_type == 'row':
            for sector in land.get('sectors', []):
                for zone in sector.get('zones', []):
                    if zone['_id'] == parent_id:
                        if 'rows' not in zone:
                            zone['rows'] = []
                        zone['rows'].append({
                            '_id': str(ObjectId()),
                            'name': request.form.get('name'),
                            'trees': []
                        })
                        break
            db.lands.update_one({'_id': ObjectId(land_id)}, {'$set': {'sectors': land['sectors']}})
            db.activities.insert_one({
                'type': 'planting',
                'notes': f'Added row {request.form.get("name")}',
                'date': datetime.utcnow()
            })
            flash('Row added successfully!', 'success')
        
        elif entity_type == 'tree':
            for sector in land.get('sectors', []):
                for zone in sector.get('zones', []):
                    for row in zone.get('rows', []):
                        if row['_id'] == parent_id:
                            if 'trees' not in row:
                                row['trees'] = []
                            row['trees'].append({
                                '_id': str(ObjectId()),
                                'name': request.form.get('name', 'Tree')
                            })
                            break
            db.lands.update_one({'_id': ObjectId(land_id)}, {'$set': {'sectors': land['sectors']}})
            db.activities.insert_one({
                'type': 'planting',
                'notes': f'Added tree {request.form.get("name", "Tree")}',
                'date': datetime.utcnow()
            })
            flash('Tree added successfully!', 'success')
        
        return redirect(url_for('lands.detail', land_id=land_id))
    
    m = folium.Map(location=[land.get('latitude', 0), land.get('longitude', 0)], zoom_start=12, width='100%', height='400px')
    folium.Marker([land.get('latitude', 0), land.get('longitude', 0)], popup=land['name']).add_to(m)
    land['map'] = m._repr_html_()
    
    return render_template('lands/detail.html', land=land)

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

@lands_bp.route('/<land_id>/sectors/<sector_id>/delete', methods=['POST'])
def delete_sector(land_id, sector_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    land = db.lands.find_one({'_id': ObjectId(land_id)})
    if land:
        land['sectors'] = [s for s in land.get('sectors', []) if s['_id'] != sector_id]
        db.lands.update_one({'_id': ObjectId(land_id)}, {'$set': {'sectors': land['sectors']}})
        log_message('warning', f'Deleted sector', session.get('user_id'), session.get('username'))
        flash('Sector deleted successfully!', 'success')
    
    return redirect(url_for('lands.detail', land_id=land_id))

@lands_bp.route('/<land_id>/sectors/<sector_id>/zones/<zone_id>/delete', methods=['POST'])
def delete_zone(land_id, sector_id, zone_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    land = db.lands.find_one({'_id': ObjectId(land_id)})
    if land:
        for sector in land.get('sectors', []):
            if sector['_id'] == sector_id:
                sector['zones'] = [z for z in sector.get('zones', []) if z['_id'] != zone_id]
                break
        db.lands.update_one({'_id': ObjectId(land_id)}, {'$set': {'sectors': land['sectors']}})
        log_message('warning', f'Deleted zone', session.get('user_id'), session.get('username'))
        flash('Zone deleted successfully!', 'success')
    
    return redirect(url_for('lands.detail', land_id=land_id))

@lands_bp.route('/<land_id>/sectors/<sector_id>/zones/<zone_id>/rows/<row_id>/delete', methods=['POST'])
def delete_row(land_id, sector_id, zone_id, row_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    land = db.lands.find_one({'_id': ObjectId(land_id)})
    if land:
        for sector in land.get('sectors', []):
            if sector['_id'] == sector_id:
                for zone in sector.get('zones', []):
                    if zone['_id'] == zone_id:
                        zone['rows'] = [r for r in zone.get('rows', []) if r['_id'] != row_id]
                        break
                break
        db.lands.update_one({'_id': ObjectId(land_id)}, {'$set': {'sectors': land['sectors']}})
        log_message('warning', f'Deleted row', session.get('user_id'), session.get('username'))
        flash('Row deleted successfully!', 'success')
    
    return redirect(url_for('lands.detail', land_id=land_id))

@lands_bp.route('/<land_id>/sectors/<sector_id>/zones/<zone_id>/rows/<row_id>/trees/<tree_id>/delete', methods=['POST'])
def delete_tree(land_id, sector_id, zone_id, row_id, tree_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    land = db.lands.find_one({'_id': ObjectId(land_id)})
    if land:
        for sector in land.get('sectors', []):
            if sector['_id'] == sector_id:
                for zone in sector.get('zones', []):
                    if zone['_id'] == zone_id:
                        for row in zone.get('rows', []):
                            if row['_id'] == row_id:
                                row['trees'] = [t for t in row.get('trees', []) if t['_id'] != tree_id]
                                break
                        break
                break
        db.lands.update_one({'_id': ObjectId(land_id)}, {'$set': {'sectors': land['sectors']}})
        log_message('warning', f'Deleted tree', session.get('user_id'), session.get('username'))
        flash('Tree deleted successfully!', 'success')
    
    return redirect(url_for('lands.detail', land_id=land_id))
