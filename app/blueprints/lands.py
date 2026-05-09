
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort
from app.database import get_db
from app.utils.logging import log_message
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


@lands_bp.route('/add', methods=['GET', 'POST'])
def add():
    print(f"[DEBUG] lands.add() - Method: {request.method}")
    print(f"[DEBUG] Form keys: {list(request.form.keys())}")
    print(f"[DEBUG] calculate value: {request.form.get('calculate')}")
    
    if request.method == 'GET':
        return render_template('lands/index.html',
                               lands=list(get_db().lands.find()),
                               calc_area=0,
                               calc_perimeter=0,
                               calc_geojson='',
                               calc_coords='')

    if 'user_id' not in session or session.get('role') not in ['admin', 'worker']:
        flash('Permission denied', 'danger')
        return redirect(url_for('lands.index'))

    if request.form.get('calculate'):
        coords = request.form.get('coordinates', '').strip()
        print(f"[DEBUG] coordinates: {coords}")
        
        if not coords:
            flash('Please enter coordinates', 'warning')
            return render_template('lands/index.html',
                                   lands=list(get_db().lands.find()),
                                   show_add_modal=True,
                                   calc_area=0,
                                   calc_perimeter=0,
                                   calc_geojson='',
                                   calc_coords='')
        
        result = convert_and_calculate(coords)

        if 'error' in result:
            flash(result['error'], 'danger')
            return render_template('lands/index.html',
                                   lands=list(get_db().lands.find()),
                                   show_add_modal=True,
                                   calc_area=0,
                                   calc_perimeter=0,
                                   calc_geojson='',
                                   calc_coords='')
        
flash('Calculation complete', 'success')
        return render_template('lands/index.html',
                               lands=list(get_db().lands.find()),
                               calc_area=result.get('area', 0),
                               calc_perimeter=result.get('perimeter', 0),
                               calc_geojson=result.get('geojson', ''),
                               calc_coords=coords,
                               show_add_modal=True,
                               active_tab='location')
    
    # Save AAdd Land
    db = get_db()
    
    try:
        # Process legal types from comma-separated string
        legal_types_str = request.form.get('legal_types', '')
        if legal_types_str:
            legal_types = [t.strip() for t in legal_types_str.split(',') if t.strip()]
        else:
            legal_types = ['Document Administratif', 'Malkiya', 'Titre']
        
        land_data = LandModel(
            farm_id=request.form.get('farm_id', ''),
            name=request.form.get('name', ''),
            legal={
                'type': legal_types,
                'deleivered': request.form.get('legal_delivered', ''),
                'date': request.form.get('legal_date', '')
            },
            owner={
                'party_id': request.form.get('owner_party_id', 'P001'),
                'name': request.form.get('owner_name', ''),
                'contact': {
                    'email': request.form.get('owner_email', ''),
                    'phone': request.form.get('owner_phone', '')
                }
            },
            location={
                'address': {
                    'street': request.form.get('street', ''),
                    'city': request.form.get('city', ''),
                    'state': request.form.get('state', ''),
                    'postal_code': request.form.get('postal_code', ''),
                    'country': request.form.get('country', '')
                },
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
        if 'address' not in location:
            location['address'] = {}
        location['address']['street'] = request.form.get('street', '')
        location['address']['city'] = request.form.get('city', '')
        location['address']['state'] = request.form.get('state', '')
        location['address']['postal_code'] = request.form.get('postal_code', '')
        location['address']['country'] = request.form.get('country', '')
        
        location['coordinates'] = {
            'latitude': float(request.form.get('latitude', 0)),
            'longitude': float(request.form.get('longitude', 0))
        }
        location['total_area'] = {'value': float(request.form.get('area', 0)), 'unit': 'acres'}
        
        # Build owner dict
        owner = land.get('owner', {})
        owner['party_id'] = request.form.get('owner_party_id', owner.get('party_id', 'P001'))
        owner['name'] = request.form.get('owner_name', '')
        if 'contact' not in owner:
            owner['contact'] = {}
        owner['contact']['email'] = request.form.get('owner_email', '')
        owner['contact']['phone'] = request.form.get('owner_phone', '')
        
        land_data = LandModel(
            farm_id=request.form.get('farm_id', land.get('farm_id', '')),
            name=request.form.get('name', ''),
            owner=owner,
            location=location,
            legal={'type': ['Document Administratif', 'Malkiya', 'Titre'], 'deleivered': '', 'date': ''},
            metadata={'established_date': '', 'last_updated': '', 'status': 'active'}
        )
        LandModel.check_duplicate(db, land_data.name, exclude_id=land_id)
        
        # Update fields
        db.lands.update_one(
            {'_id': ObjectId(land_id)}, 
            {'$set': {
                'farm_id': land_data.farm_id,
                'name': land_data.name,
                'owner': owner,
                'location': location,
                'legal': land_data.legal
            }}
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
        try:
            import json
            
            # Parse boundary if provided
            boundary = None
            boundary_str = request.form.get('boundary', '').strip()
            if boundary_str:
                try:
                    boundary = json.loads(boundary_str)
                except:
                    boundary = {'type': 'Polygon', 'coordinates': []}
            else:
                boundary = {'type': 'Polygon', 'coordinates': []}
            
            # Get sector_id and sector_number
            sector_id = request.form.get('sector_id', '').strip()
            sector_number = request.form.get('sector_number', 1)
            try:
                sector_number = int(sector_number)
            except:
                sector_number = 1
            
            # Validate with SectorModel
            sector_data = SectorModel(
                sector_id=sector_id,
                sector_number=sector_number,
                name=request.form.get('name', ''),
                description=request.form.get('description', ''),
                location={
                    'area': {'value': float(request.form.get('area', 0) or 0), 'unit': request.form.get('area_unit', 'acres')},
                    'soil_type': request.form.get('soil_type', 'loam'),
                    'slope': request.form.get('slope', ''),
                    'irrigation_type': request.form.get('irrigation_type', '')
                },
                boundary=boundary,
                metadata={
                    'status': request.form.get('status', 'active'),
                    'notes': request.form.get('notes', '')
                }
            )
            
            land = db.lands.find_one({'_id': ObjectId(land_id)})
            if land:
                if 'sectors' not in land:
                    land['sectors'] = []
                
                sector_dict = sector_data.model_dump()
                sector_dict['_id'] = str(ObjectId())
                sector_dict['zones'] = []
                
                land['sectors'].append(sector_dict)
                db.lands.update_one({'_id': ObjectId(land_id)}, {'$set': {'sectors': land['sectors']}})
                log_message('info', f"Added sector: {sector_data.name}", session.get('user_id'), session.get('username'))
                flash('Sector added successfully!', 'success')
            return redirect(url_for('lands.detail', land_id=land_id))
        except Exception as e:
            flash(f'Validation error: {str(e)}', 'danger')
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

@lands_bp.route('/<land_id>/upload_photo', methods=['POST'])
def upload_photo(land_id):
    
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

@lands_bp.route('/<land_id>/delete_photo/<filename>', methods=['POST'])
def delete_photo(land_id, filename):
    
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
