import sys
import traceback
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort
from app.database import get_db
from app.utils.logging import log_message, log_func_call, login_required, admin_required
from app.utils.calculation import convert_and_calculate
from app.utils.map_utils import build_lands_map, build_land_detail_map
from app.models.validation import LandModel, SectorModel, ZoneModel, RowModel, TreeModel
from bson import ObjectId
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import json

lands_bp = Blueprint('lands', __name__, url_prefix='/lands')
lands_bp.strict_slashes = False

UPLOAD_FOLDER = 'static/uploads/lands'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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
@admin_required
@lands_bp.route('/add', methods=['GET', 'POST'])
def add():
    try:
        if request.method == 'GET':
            log_message('info', f"[LAND] Add page - User: {session.get('username')}")
            db = get_db()
            if isinstance(db, dict) and db.get('error'):
                flash(f'Database error: {db["message"]}', 'danger')
                return render_template('lands/index.html', lands=[], lands_farms_json='{}')
            lands = list(db.lands.find())
            lands_farms = {}
            for land in lands:
                land['_id'] = str(land['_id'])
                lands_farms[land['_id']] = [{
                    '_id': str(farm.get('_id', '')),
                    'farm_name': farm.get('farm_name', farm.get('name', ''))
                } for farm in land.get('farms', [])]
            return render_template('lands/index.html',
                                   lands=lands, lands_farms_json=json.dumps(lands_farms))
        
        log_message('info', f"[LAND] Add form submitted - User: {session.get('username')}")

        if 'user_id' not in session or session.get('role') not in ['admin', 'worker']:
            flash('Permission denied', 'danger')
            return redirect(url_for('lands.index'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('lands.index'))
        
        try:
            # Get form data
            land_id = request.form.get('land_id', '')
            name = request.form.get('name', '')
            street = request.form.get('street', '')
            city = request.form.get('city', '')
            latitude_str = request.form.get('latitude', '')
            longitude_str = request.form.get('longitude', '')
            altitude_str = request.form.get('altitude', '0')
            
            # Initialize location data
            location_data = {
                'address': {
                    'street': '',
                    'city': '',
                },
                'center_coordinate': {
                    'latitude': 0.0,
                    'longitude': 0.0
                },
                'altitude': 0.0,
            }
            
            # Process coordinates if provided
            latitude = 0.0
            longitude = 0.0
            altitude = 0.0
            if latitude_str and longitude_str:
                try:
                    latitude = float(latitude_str)
                    longitude = float(longitude_str)
                    location_data['center_coordinate'] = {
                        'latitude': latitude,
                        'longitude': longitude
                    }
                    
                    # If street or city is empty, try to get from reverse geocoding
                    if (not street or not city) and latitude != 0.0 and longitude != 0.0:
                        from app.utils.map_utils import latlon_to_dms_and_address
                        try:
                            addr_info = latlon_to_dms_and_address(latitude, longitude)
                            if not street:
                                address = addr_info.get('address', '')
                                if address:
                                    location_data['address']['street'] = address.split(',')[0].strip()
                            if not city and address:
                                address_parts = address.split(',')
                                if len(address_parts) >= 2:
                                    location_data['address']['city'] = address_parts[1].strip()
                        except Exception:
                            pass
                    
                    # If altitude is not set or is default, try to get from elevation service
                    altitude_val = float(altitude_str) if altitude_str else 0.0
                    if altitude_val == 0.0 and latitude != 0.0 and longitude != 0.0:
                        try:
                            from app.utils.map_utils import get_altitude_meters
                            altitude = get_altitude_meters(latitude, longitude)
                            if altitude is not None:
                                altitude_val = altitude
                        except Exception:
                            pass
                    
                    location_data['altitude'] = altitude_val
                except ValueError:
                    pass
            
            # Process altitude if manually set
            try:
                altitude_val = float(altitude_str) if altitude_str else 0.0
                if altitude_val != 0.0:
                    location_data['altitude'] = altitude_val
            except ValueError:
                pass
            
            land_data = LandModel(
                land_id=land_id,
                name=name,
                location=location_data,
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
            land_dict['created_at'] = datetime.utcnow()
            land_dict['last_updated_at'] = datetime.utcnow()
            db.lands.insert_one(land_dict)
            log_message('info', f"Added land: {land_data.name}", session.get('user_id'), session.get('username'))
            flash('Land added successfully!', 'success')
        except Exception as e:
            flash(f'Validation error: {str(e)}', 'danger')
        
        return redirect(url_for('lands.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"lands.add() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error: {err["message"]}', 'danger')
        return redirect(url_for('lands.index'))


@log_func_call
@admin_required
@lands_bp.route('/<land_id>/edit', methods=['POST'])
def edit(land_id):
    try:
        log_message('info', f"[LAND] Edit Land form submitted - Land ID: {land_id} - User: {session.get('username')}")

        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('lands.index'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('lands.index'))
        land = db.lands.find_one({'_id': ObjectId(land_id)})
        if not land:
            abort(404)
        
        try:
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
            location['altitude'] = float(request.form.get('altitude', 0))
            location['total_area'] = {'value': float(request.form.get('area', 0)), 'unit': 'ha'}
            
            metadata = land.get('metadata', {})
            metadata['established_date'] = request.form.get('established_date', '')
            metadata['last_updated'] = datetime.utcnow()
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
            
            db.lands.update_one(
                {'_id': ObjectId(land_id)}, 
                {'$set': {
                    'land_id': land_data.land_id,
                    'name': land_data.name,
                    'location': location,
                    'metadata': metadata,
                    'last_updated_at': datetime.utcnow()
                }}
            )
            log_message('info', f"Updated land: {land_data.name}", session.get('user_id'), session.get('username'))
            flash('Land updated successfully!', 'success')
        except Exception as e:
            flash(f'Validation error: {str(e)}', 'danger')
        
        return redirect(url_for('lands.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"lands.edit() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error editing land: {err["message"]}', 'danger')
        return redirect(url_for('lands.index'))


@log_func_call
@login_required
@lands_bp.route('/', methods=['GET'])
def index():
    try:
        log_message('info', f"[LAND] Index page - User: {session.get('username')}")
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return render_template('lands/index.html', lands=[], search='', lands_farms_json='{}')
        search = request.args.get('search', '').strip()
        
        query = {}
        if search:
            query['name'] = {'$regex': search, '$options': 'i'}
        
        lands = list(db.lands.find(query))
        
        for land in lands:
            land['_id'] = str(land['_id'])
            land['sector_count'] = sum(len(farm.get('sectors', [])) for farm in land.get('farms', []))
        
        lands_farms = {}
        for land in lands:
            lands_farms[land['_id']] = [{
                '_id': str(farm.get('_id', '')),
                'farm_name': farm.get('farm_name', farm.get('name', ''))
            } for farm in land.get('farms', [])]

        return render_template('lands/index.html', lands=lands, search=search, lands_farms_json=json.dumps(lands_farms), form_data={})
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"lands.index() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error: {err["message"]}', 'danger')
        return render_template('lands/index.html', lands=[], search='', lands_farms_json='{}', form_data={})


@log_func_call
@login_required
@lands_bp.route('/<land_id>', methods=['GET', 'POST'])
def detail(land_id):
    try:
        log_message('info', f"Detail Land {land_id} - Method {request.method} | {session.get('username')}")
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('lands.index'))
        land = db.lands.find_one({'_id': ObjectId(land_id)})
        
        if not land:
            flash('Land not found', 'danger')
            return redirect(url_for('lands.index'))
        
        land['_id'] = str(land['_id'])
        
        if request.method == 'POST' and session.get('role') == 'admin':
            entity_type = request.form.get('entity_type')
            parent_id = request.form.get('parent_id')
            
            if entity_type == 'sector':
                farm_id = request.form.get('farm_id', '')
                if not farm_id:
                    flash('Farm is required to add a sector', 'danger')
                    return redirect(url_for('lands.detail', land_id=land_id))
                for farm in land.get('farms', []):
                    if farm.get('_id') == farm_id or str(farm.get('_id', '')) == farm_id:
                        if 'sectors' not in farm:
                            farm['sectors'] = []
                        farm['sectors'].append({
                            '_id': str(ObjectId()),
                            'name': request.form.get('name'),
                            'zones': [],
                            'farm_id': farm_id
                        })
                        db.lands.update_one({'_id': ObjectId(land_id)}, {'$set': {'farms': land.get('farms', []), 'last_updated_at': datetime.now().isoformat()}})
                        db.activities.insert_one({
                            'type': 'planting',
                            'notes': f'Added sector {request.form.get("name")} to {land.get("name", "")}',
                            'date': datetime.utcnow()
                        })
                        flash('Sector added successfully!', 'success')
                        break
                else:
                    flash('Farm not found', 'danger')
            
            elif entity_type == 'zone':
                for farm in land.get('farms', []):
                    for sector in farm.get('sectors', []):
                        if sector.get('_id') == parent_id:
                            if 'zones' not in sector:
                                sector['zones'] = []
                            sector['zones'].append({
                                '_id': str(ObjectId()),
                                'name': request.form.get('name'),
                                'rows': []
                            })
                            break
                db.lands.update_one({'_id': ObjectId(land_id)}, {'$set': {'farms': land.get('farms', []), 'last_updated_at': datetime.now().isoformat()}})
                db.activities.insert_one({
                    'type': 'planting',
                    'notes': f'Added zone {request.form.get("name")}',
                    'date': datetime.utcnow()
                })
                flash('Zone added successfully!', 'success')
            
            elif entity_type == 'row':
                for farm in land.get('farms', []):
                    for sector in farm.get('sectors', []):
                        for zone in sector.get('zones', []):
                            if zone.get('_id') == parent_id:
                                if 'rows' not in zone:
                                    zone['rows'] = []
                                zone['rows'].append({
                                    '_id': str(ObjectId()),
                                    'name': request.form.get('name'),
                                    'trees': []
                                })
                                break
                db.lands.update_one({'_id': ObjectId(land_id)}, {'$set': {'farms': land.get('farms', []), 'last_updated_at': datetime.now().isoformat()}})
                db.activities.insert_one({
                    'type': 'planting',
                    'notes': f'Added row {request.form.get("name")}',
                    'date': datetime.utcnow()
                })
                flash('Row added successfully!', 'success')
            
            elif entity_type == 'tree':
                for farm in land.get('farms', []):
                    for sector in farm.get('sectors', []):
                        for zone in sector.get('zones', []):
                            for row in zone.get('rows', []):
                                if row.get('_id') == parent_id:
                                    if 'trees' not in row:
                                        row['trees'] = []
                                    row['trees'].append({
                                        '_id': str(ObjectId()),
                                        'name': request.form.get('name', 'Tree')
                                    })
                                    break
                db.lands.update_one({'_id': ObjectId(land_id)}, {'$set': {'farms': land.get('farms', []), 'last_updated_at': datetime.now().isoformat()}})
                db.activities.insert_one({
                    'type': 'planting',
                    'notes': f'Added tree {request.form.get("name", "Tree")}',
                    'date': datetime.utcnow()
                })
                flash('Tree added successfully!', 'success')
            
            return redirect(url_for('lands.detail', land_id=land_id))
        
        land['map'] = build_land_detail_map(land, height=400)
        
        return render_template('lands/detail.html', land=land)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"lands.detail() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error: {err["message"]}', 'danger')
        return redirect(url_for('lands.index'))


@log_func_call
@admin_required
@lands_bp.route('/<land_id>/delete', methods=['POST'])
def delete(land_id):
    try:
        log_message('info', f"[LAND] Delete Land request - Land ID: {land_id} - User: {session.get('username')}")
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('lands.index'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('lands.index'))
        land = db.lands.find_one({'_id': ObjectId(land_id)})
        if land:
            db.lands.delete_one({'_id': ObjectId(land_id)})
            log_message('warning', f'Deleted land {land.get("name", "")}', session.get('user_id'), session.get('username'))
            flash('Land deleted successfully!', 'success')
        
        return redirect(url_for('lands.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"lands.delete() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error deleting land: {err["message"]}', 'danger')
        return redirect(url_for('lands.index'))


@log_func_call
@admin_required
@lands_bp.route('/<land_id>/delete_zone/<sector_id>/<zone_id>', methods=['POST'])
def delete_zone(land_id, sector_id, zone_id):
    try:
        log_message('info', f"[LAND] Delete Zone request - Land: {land_id}, Sector: {sector_id}, Zone: {zone_id}")
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('lands.index'))
        land = db.lands.find_one({'_id': ObjectId(land_id)})
        if not land:
            flash('Land not found', 'danger')
            return redirect(url_for('lands.index'))
        result = db.lands.update_one(
            {'_id': ObjectId(land_id), 'farms.sectors._id': sector_id},
            {'$pull': {'farms.$[].sectors.$[s].zones': {'_id': zone_id}}},
            array_filters=[{'s._id': sector_id}]
        )
        if result.modified_count > 0:
            flash('Zone deleted successfully!', 'success')
        else:
            flash('Zone not found', 'danger')
        return redirect(url_for('zones.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"lands.delete_zone() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error deleting zone: {err["message"]}', 'danger')
        return redirect(url_for('zones.index'))


@log_func_call
@admin_required
@lands_bp.route('/<land_id>/upload_photo', methods=['POST'])
def upload_photo(land_id):
    try:
        log_message('info', f"Upload Photo Land {land_id} - Method {request.method} | {session.get('username')}")
        if 'user_id' not in session or session.get('role') not in ['admin', 'worker']:
            abort(403)
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('lands.detail', land_id=land_id))
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
            {'$set': {'photos': uploaded_photos, 'last_updated_at': datetime.now().isoformat()}}
        )
        
        log_message('info', f'Uploaded {len(photos)} photo(s) to land', session.get('user_id'), session.get('username'))
        flash('Photos uploaded successfully!', 'success')
        return redirect(url_for('lands.detail', land_id=land_id))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"lands.upload_photo() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error uploading photos: {err["message"]}', 'danger')
        return redirect(url_for('lands.detail', land_id=land_id))


@log_func_call
@admin_required
@lands_bp.route('/<land_id>/delete_photo/<filename>', methods=['POST'])
def delete_photo(land_id, filename):
    try:
        log_message('info', f"Delete Photo Land {land_id} - Method {request.method} | {session.get('username')}")
        if 'user_id' not in session or session.get('role') not in ['admin', 'worker']:
            abort(403)
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('lands.detail', land_id=land_id))
        land = db.lands.find_one({'_id': ObjectId(land_id)})
        if not land:
            abort(404)
        
        photos = land.get('photos', [])
        photo_to_delete = None
        
        for photo in photos:
            if photo.get('filename') == filename:
                photo_to_delete = photo
                break
        
        if photo_to_delete:
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            
            photos = [p for p in photos if p.get('filename') != filename]
            db.lands.update_one(
                {'_id': ObjectId(land_id)},
                {'$set': {'photos': photos, 'last_updated_at': datetime.now().isoformat()}}
            )
            
            log_message('warning', f'Deleted photo {filename} from land', session.get('user_id'), session.get('username'))
            flash('Photo deleted successfully!', 'success')
        
        return redirect(url_for('lands.detail', land_id=land_id))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"lands.delete_photo() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error deleting photo: {err["message"]}', 'danger')
        return redirect(url_for('lands.detail', land_id=land_id))
