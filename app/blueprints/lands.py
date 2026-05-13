
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort

from app.database import get_db
from app.utils.logging import log_message, log_func_call, login_required, admin_required
from app.utils.calculation import convert_and_calculate
from app.models.validation import LandModel, SectorModel, ZoneModel, RowModel, TreeModel
from bson import ObjectId
from datetime import datetime
import folium
import os
from werkzeug.utils import secure_filename


lands_bp = Blueprint('lands', __name__, url_prefix='/lands')
lands_bp.strict_slashes = False

UPLOAD_FOLDER = 'static/uploads/lands'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@log_func_call
@admin_required
@lands_bp.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'GET':
        log_message('info', f"[LAND] Add page - User: {session.get('username')}")
        return render_template('lands/index.html',
                               lands=list(get_db().lands.find()))
    
    log_message('info', f"[LAND] Add form submitted - User: {session.get('username')}")

    if 'user_id' not in session or session.get('role') not in ['admin', 'worker']:
        flash('Permission denied', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    
    try:
        land_data = LandModel(
            land_id=request.form.get('land_id', ''),
            name=request.form.get('name', ''),
            location={
                'address': {
                    'street': request.form.get('street', ''),
                    'city': request.form.get('city', ''),
                },
                'center_coordinate': {
                    'latitude': float(request.form.get('latitude', 0)),
                    'longitude': float(request.form.get('longitude', 0))
                },
                'altitude': {
                    'minimum': float(request.form.get('altitude_min', 0)),
                    'maximum': float(request.form.get('altitude_max', 0))
                },
            },
            metadata={
                'established_date': request.form.get('established_date', ''),
                'last_updated': '',
                'status': request.form.get('status', 'active'),
                'notes': request.form.get('notes', ''),
                'version': int(request.form.get('version', 1))
            }
        )
        LandModel.check_duplicate(db, land_data.name)
        land_dict = land_data.model_dump()
        # land_dict['lands'] = []
        db.lands.insert_one(land_dict)
        log_message('info', f"Added land: {land_data.name}", session.get('user_id'), session.get('username'))
        flash('Land added successfully!', 'success')
    except Exception as e:
        flash(f'Validation error: {str(e)}', 'danger')
    
    return redirect(url_for('lands.index'))

@log_func_call
@admin_required
@lands_bp.route('/<land_id>/edit', methods=['POST'])
def edit(land_id):
    log_message('info', f"[LAND] Edit Land form submitted - Land ID: {land_id} - User: {session.get('username')}")

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
        if 'address' not in location:
            location['address'] = {}
        location['address']['street'] = request.form.get('street', '')
        location['address']['city'] = request.form.get('city', '')
        location['address']['state'] = request.form.get('state', '')
        location['address']['postal_code'] = request.form.get('postal_code', '')
        location['address']['country'] = request.form.get('country', '')
        
        location['city'] = request.form.get('city', '')
        location['center_coordinate'] = {
            'latitude': float(request.form.get('latitude', 0)),
            'longitude': float(request.form.get('longitude', 0))
        }
        location['altitude'] = {
            'minimum': float(request.form.get('altitude_min', 0)),
            'maximum': float(request.form.get('altitude_max', 0))
        }
        location['total_area'] = {'value': float(request.form.get('area', 0)), 'unit': 'ha'}
        
        metadata = land.get('metadata', {})
        metadata['established_date'] = request.form.get('established_date', '')
        metadata['last_updated'] = datetime.now().isoformat()
        metadata['status'] = request.form.get('status', 'active')
        metadata['notes'] = request.form.get('notes', '')
        metadata['version'] = int(request.form.get('version', 1))
        
        land_data = LandModel(
            land_id=request.form.get('land_id', land.get('land_id', '')),
            name=request.form.get('name', ''),
            location=location,
            metadata=metadata
        )
        LandModel.check_duplicate(db, land_data.name, exclude_id=land_id)
        
        # Update fields
        db.lands.update_one(
            {'_id': ObjectId(land_id)}, 
            {'$set': {
                'land_id': land_data.land_id,
                'name': land_data.name,
                'location': location,
                'metadata': metadata
            }}
        )
        log_message('info', f"Updated land: {land_data.name}", session.get('user_id'), session.get('username'))
        flash('Land updated successfully!', 'success')
    except Exception as e:
        flash(f'Validation error: {str(e)}', 'danger')
    
    return redirect(url_for('lands.index'))

@log_func_call
@login_required
@lands_bp.route('/', methods=['GET'])
def index():
    log_message('info', f"[LAND] Index page - User: {session.get('username')}")
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

@log_func_call
@login_required
@lands_bp.route('/<land_id>', methods=['GET', 'POST'])
def detail(land_id):
    log_message('info', f"Detail Land {land_id} - Method {request.method} | {session.get('username')}")
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

@log_func_call
@admin_required
@lands_bp.route('/<land_id>/delete', methods=['POST'])
def delete(land_id):
    log_message('info', f"[LAND] Delete Land request - Land ID: {land_id} - User: {session.get('username')}")
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

@log_func_call
@admin_required
@lands_bp.route('/<land_id>/upload_photo', methods=['POST'])
def upload_photo(land_id):
    log_message('info', f"Upload Photo Land {land_id} - Method {request.method} | {session.get('username')}")
    if 'user_id' not in session or session.get('role') not in ['admin', 'worker']:
        abort(403)
    
    db = get_db()
    land = db.lands.find_one({'_id': ObjectId(land_id)})
    if not land:
        abort(404)
    
    photos = request.files.getlist('photos')
    descriptions = request.form.getlist('descriptions[]')
    
    uploaded_photos = land.get('photos', [])
    
    for i, photo in enumerate(photos):
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            new_filename = timestamp + filename
            photo_path = os.path.join(UPLOAD_FOLDER, new_filename)
            photo.save(photo_path)
            
            description = descriptions[i] if i < len(descriptions) else ''
            
            uploaded_photos.append({
                'filename': new_filename,
                'path': f'/static/uploads/lands/{new_filename}',
                'description': description,
                'uploaded_at': datetime.now().isoformat()
            })
    
    db.lands.update_one(
        {'_id': ObjectId(land_id)},
        {'$set': {'photos': uploaded_photos}}
    )
    
    log_message('info', f'Uploaded {len(photos)} photo(s) to land', session.get('user_id'), session.get('username'))
    flash('Photos uploaded successfully!', 'success')
    return redirect(url_for('lands.detail', land_id=land_id))

@log_func_call
@admin_required
@lands_bp.route('/<land_id>/delete_photo/<filename>', methods=['POST'])
def delete_photo(land_id, filename):
    log_message('info', f"Delete Photo Land {land_id} - Method {request.method} | {session.get('username')}")
    if 'user_id' not in session or session.get('role') not in ['admin', 'worker']:
        abort(403)
    
    db = get_db()
    land = db.lands.find_one({'_id': ObjectId(land_id)})
    if not land:
        abort(404)
    
    photos = land.get('photos', [])
    photo_to_delete = None
    
    for photo in photos:
        if photo['filename'] == filename:
            photo_to_delete = photo
            break
    
    if photo_to_delete:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        photos = [p for p in photos if p['filename'] != filename]
        db.lands.update_one(
            {'_id': ObjectId(land_id)},
            {'$set': {'photos': photos}}
        )
        
        log_message('warning', f'Deleted photo {filename} from land', session.get('user_id'), session.get('username'))
        flash('Photo deleted successfully!', 'success')
    
    return redirect(url_for('lands.detail', land_id=land_id))
