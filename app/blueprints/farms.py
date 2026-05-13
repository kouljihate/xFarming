from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort, jsonify
from app.database import get_db
from app.utils.logging import log_message, log_func_call, login_required, admin_required
from app.utils.calculation import convert_and_calculate, calculate_centroid, calculate_polygon_metrics, parse_simple_coordinates
from app.models.validation import FarmModel
from bson import ObjectId
from datetime import datetime
from app.utils.map_browsing import generate_map

farms_bp = Blueprint('farms', __name__, url_prefix='/farms')
farms_bp.strict_slashes = False


@log_func_call
@login_required
@farms_bp.route('/')
def index():
    log_message('info', f"[FARM] Index page - User: {session.get('username')}")
    
    db = get_db()
    search = request.args.get('search', '').strip()
    lands = list(db.lands.find())
    farms = []
    lands_for_select = []
    
    show_add = request.args.get('show_add_modal', '')
    if show_add:
        log_message('info', f"[FARM] Add page opened - User: {session.get('username')}")
    
    for land in lands:
        land['_id'] = str(land['_id'])
        lands_for_select.append(land)
        for farm in land.get('farms', []):
            farm['_id'] = str(farm.get('_id', ''))
            if search and search.lower() not in farm['name'].lower():
                continue
            farm['land'] = land
            farm['land_id'] = land['_id']
            farm['sector_count'] = len(farm.get('sectors', []))
            farms.append(farm)
    
    return render_template('farms/index.html', farms=farms, lands=lands_for_select, search=search, form_data={})


@log_func_call
@login_required
@farms_bp.route('/calculate', methods=['POST'])
def calculate():
    log_message('info', f"Calculate Farm - Method {request.method} | {session.get('username')}")
    
    coords = request.form.get('coordinates', '').strip()
    result = convert_and_calculate(coords)
    
    if 'error' in result:
        flash(result['error'], 'danger')
        return redirect(url_for('farms.index'))
    
    return render_template('farms/index.html', 
                           lands=list(get_db().lands.find()),
                           calc_area=result['area_ha'],
                           calc_perimeter=result['perimeter_m'],
                           calc_geojson=result['geojson'],
                           calc_coords=coords)


@log_func_call
@admin_required
@farms_bp.route('/add', methods=['POST'])
def add():
    log_message('info', f"[FARM] Add Farm attempt - User: {session.get('username')} | Role: {session.get('role')}")
    
    # Get Form Data in One shot in Json/Dict Format
    form_data = request.form.to_dict()
    log_message('info', f"[FARM] Add Farm Form Data: {form_data}")

        
    action = form_data.get("action")
    
    if action == "calculate":
        log_message('info', f"[FARM] Calculate Farm attempt - User: {session.get('username')} | Role: {session.get('role')}")
        
        coords = request.form.get('coordinates', '').strip()
        coords = parse_simple_coordinates(coords)
        result_polygon = calculate_polygon_metrics(coords)
        result_centroid = calculate_centroid(coords)
        
        log_message('info', f"[FARM] Calculate Polygon Result: {result_polygon}")  
        log_message('info', f"[FARM] Calculate Centroid Result: {result_centroid}")
        
        if 'error' in result_polygon or 'error' in result_centroid:
            log_message('error', f"[FARM] Calculate Farm Error: {result_polygon['error'] or result_centroid['error']}")
            flash(result_polygon['error'] or result_centroid['error'], 'danger')
            db = get_db()
            lands = list(db.lands.find())
            for land in lands:
                land['_id'] = str(land['_id'])
            return render_template('farms/index.html', farms=[], lands=lands, show_add_modal=True, form_data=request.form.to_dict(flat=True))
        
        db = get_db()
        lands = list(db.lands.find())
        for land in lands:
            land['_id'] = str(land['_id'])
        
        return render_template('farms/index.html', 
                            #    farms=[],
                               lands=lands,
                               calc_area=result_polygon['area_ha'],
                               calc_perimeter=result_polygon['perimeter_m'],
                               calc_center_lat=result_centroid['latitude'],
                               calc_center_lon=result_centroid['longitude'],
                               calc_coords=coords,
                               calc_geojson=result_polygon.get('geojson', ''),
                               google_map_url=result_centroid['maps_url'],
                               show_add_modal=True,
                               form_data=request.form.to_dict(flat=True),
                               active_tab='')
    
    if action == "show_map":
        log_message('info', f"[FARM] Show Map attempt - User: {session.get('username')} | Role: {session.get('role')}")
        generate_map(
            result_centroid,
            label=f"Farm Parcel — {request.form.get('name')}",
            output_path="map.html",
            open_browser=True,   # set False to skip auto-open
        )

        db = get_db()
        lands = list(db.lands.find())
        for land in lands:
            land['_id'] = str(land['_id'])
        return render_template('farms/index.html',
                               farms=[],
                               lands=lands,
                               show_add_modal=True,
                               form_data=request.form.to_dict(flat=True),
                               active_tab='')

    


    # db = get_db()
    # land_id = request.form.get('land_id')
    
    try:
        import json
        import os
        from werkzeug.utils import secure_filename
        
        boundary = None
        boundary_str = request.form.get('boundary', '').strip()
        if boundary_str:
            try:
                boundary = json.loads(boundary_str)
            except:
                boundary = {'type': 'Polygon', 'coordinates': []}
        else:
            boundary = {'type': 'Polygon', 'coordinates': []}
        
        farm_id = request.form.get('farm_id', '').strip()
        # farm_number = request.form.get('farm_number', 1)
        try:
            farm_id = int(farm_id)
        except:
            farm_id = 1
        
        photos = []
        files = request.files.getlist('photos')
        if files and files[0].filename:
            upload_dir = os.path.join('static', 'uploads', 'farms')
            os.makedirs(upload_dir, exist_ok=True)
            for file in files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{timestamp}_{filename}"
                    filepath = os.path.join(upload_dir, filename)
                    file.save(filepath)
                    photo_desc = request.form.get('photo_description', '')
                    photos.append({
                        'filename': filename,
                        'path': f'/static/uploads/farms/{filename}',
                        'description': photo_desc,
                        'uploaded_at': datetime.now().isoformat()
                    })
        
        farm_data = FarmModel(
            farm_id=farm_id,
            # farm_number=farm_number,
            farm_name=request.form.get('farm_name', ''),
            description=request.form.get('description', ''),
            location={
                'area': {'value': float(request.form.get('area', 0) or 0), 'unit': request.form.get('area_unit', 'ha')},
                'map_google_url': request.form.get('google_map_url', ''),
            },
            soil_topography_climate={
                'soil_type': request.form.get('soil_type', 'loam'),
                'topography': request.form.get('topography', ''),
                'climate_zone': request.form.get('climate_zone', '')
            },
            boundary=boundary,
            irrigation_system={
                'type': request.form.get('irrigation_type', ''),
                'source': request.form.get('irrigation_source', ''),
                'capacity_lph': int(request.form.get('irrigation_capacity', 0) or 0),
                'notes': request.form.get('irrigation_notes', '')
            },
            legal={
                'registration_number': request.form.get('registration_number', ''),
                'lease_status': request.form.get('lease_status', 'owned'),
                'lease_expiry': request.form.get('lease_expiry', ''),
                'documents': request.form.get('legal_docs', '')
            },
            photos=photos,
            metadata={
                'status': request.form.get('status', 'active'),
                'notes': request.form.get('notes', '')
            }
        )


        # need to push the farm_data into the appropriate land in db.lands collection
        db.lands.update_one(
            {'_id': ObjectId(request.form.get('land_id', ''))},
            {
                '$push': {
                    'farms': farm_data.model_dump()
                }
            }
        )

        # need to push activity
        db.activities.insert_one({
            'type': 'web',
            'operation': 'farms',
            'action': 'added',
            'notes': f"Added farm '{farm_data.name} - {farm_id}' to land '{request.form.get('land_name', '')}'",
            'date': datetime.utcnow(),
            'user_id': session.get('user_id'),
            'username': session.get('username')
        })



        
        log_message('info', f"[FARM] Added farm: {farm_data.name}", session.get('user_id'), session.get('username'))
        flash('Farm added successfully!', 'success')
        return redirect(url_for('farms.index', land_id=request.form.get('land_id', '')))


        
        # lands = list(db.lands.find())
        # for land in lands:
        #     if str(land['_id']) == land_id:
        #         farm_dict = farm_data.model_dump()
        #         farm_dict['_id'] = str(ObjectId())
        #         farm_dict['sectors'] = []
                
        #         if 'farms' not in land:
        #             land['farms'] = []
        #         land['farms'].append(farm_dict)
        #         db.lands.update_one({'_id': land['_id']}, {'$set': {'farms': land.get('farms', [])}})
        #         db.activities.insert_one({
        #             'type': 'planting',
        #             'notes': f"Added farm '{farm_data.name}' to land '{land['name']}'",
        #             'date': datetime.utcnow(),
        #             'user_id': session.get('user_id'),
        #             'username': session.get('username')
        #         })
        #         log_message('info', f"Added farm: {farm_data.name}", session.get('user_id'), session.get('username'))
        #         flash('Farm added successfully!', 'success')
        #         break
    except Exception as e:
        
        log_message('error', f"[FARM] Add Farm failed - User: {session.get('username')} - Error: {str(e)}")
        flash(f'Validation error: {str(e)}', 'danger')
    
    return redirect(url_for('farms.index'))


@log_func_call
@login_required
@farms_bp.route('/<farm_id>')
def detail(farm_id):
    log_message('info', f"Detail Farm {farm_id} - Method {request.method} | {session.get('username')}")
    
    db = get_db()
    lands = list(db.lands.find())
    
    for land in lands:
        for farm in land.get('farms', []):
            if farm['_id'] == farm_id:
                farm['land'] = land
                farm['_id'] = str(farm['_id'])
                
                for sector in farm.get('sectors', []):
                    sector['_id'] = str(sector.get('_id', ''))
                    sector['zone_count'] = len(sector.get('zones', []))
                    for zone in sector.get('zones', []):
                        zone['_id'] = str(zone.get('_id', ''))
                        zone['row_count'] = len(zone.get('rows', []))
                        for row in zone.get('rows', []):
                            row['_id'] = str(row.get('_id', ''))
                            row['tree_count'] = len(row.get('trees', []))
                
                return render_template('farms/detail.html', farm=farm, land=land, sectors=farm.get('sectors', []))
    
    abort(404)


@log_func_call
@admin_required
@farms_bp.route('/<farm_id>/edit', methods=['GET', 'POST'])
def edit(farm_id):
    if request.method == 'GET':
        log_message('info', f"[FARM] Edit Farm modal opened - Farm ID: {farm_id} - User: {session.get('username')}")
    else:
        log_message('info', f"[FARM] Edit Farm form submitted - Farm ID: {farm_id} - User: {session.get('username')}")
    
    db = get_db()
    lands = list(db.lands.find())
    
    for land in lands:
        for farm in land.get('farms', []):
            if farm['_id'] == farm_id:
                if request.method == 'POST':
                    try:
                        import json
                        
                        boundary = None
                        boundary_str = request.form.get('boundary', '').strip()
                        if boundary_str:
                            try:
                                boundary = json.loads(boundary_str)
                            except:
                                boundary = farm.get('boundary', {'type': 'Polygon', 'coordinates': []})
                        else:
                            boundary = farm.get('boundary', {'type': 'Polygon', 'coordinates': []})
                        
                        farm_id = request.form.get('farm_id', '').strip()
                        # farm_number = request.form.get('farm_number', farm.get('farm_number', 1))
                        try:
                            farm_id = int(farm_id)
                        except:
                            farm_id = 1
                        
                        farm_data = FarmModel(
                            farm_id=str(farm_id),
                            # farm_number=farm_number,
                            name=request.form.get('name', ''),
                            description=request.form.get('description', ''),
                            location={
                                'area': {'value': float(request.form.get('area', 0) or 0), 'unit': request.form.get('area_unit', 'ha')},
                                'soil_type': request.form.get('soil_type', 'loam'),
                                'topography': request.form.get('topography', ''),
                                'climate_zone': request.form.get('climate_zone', '')
                            },
                            boundary=boundary,
                            irrigation_system={
                                'type': request.form.get('irrigation_type', ''),
                                'source': request.form.get('irrigation_source', ''),
                                'capacity_lph': int(request.form.get('irrigation_capacity', 0) or 0),
                                'notes': request.form.get('irrigation_notes', '')
                            },
                            legal={
                                'registration_number': request.form.get('registration_number', ''),
                                'lease_status': request.form.get('lease_status', 'owned'),
                                'lease_expiry': request.form.get('lease_expiry', ''),
                                'documents': request.form.get('legal_docs', '')
                            },
                            metadata={
                                'status': request.form.get('status', 'active'),
                                'notes': request.form.get('notes', '')
                            }
                        )
                        
                        farm['farm_id'] = farm_data.farm_id
                        # farm['farm_number'] = farm_data.farm_number
                        farm['name'] = farm_data.name
                        farm['description'] = farm_data.description
                        farm['location'] = farm_data.location
                        farm['boundary'] = farm_data.boundary
                        farm['irrigation_system'] = farm_data.irrigation_system
                        farm['legal'] = farm_data.legal
                        farm['metadata'] = farm_data.metadata
                        
                        db.lands.update_one({'_id': land['_id']}, {'$set': {'farms': land.get('farms', [])}})
                        log_message('info', f"Updated farm: {farm_data.name}", session.get('user_id'), session.get('username'))
                        flash('Farm updated successfully!', 'success')
                    except Exception as e:
                        flash(f'Validation error: {str(e)}', 'danger')
                    return redirect(url_for('farms.index'))
                else:
                    return render_template('farms/edit.html', farm=farm, land=land)
    
    abort(404)


@log_func_call
@admin_required
@farms_bp.route('/<farm_id>/delete', methods=['POST'])
def delete(farm_id):
    log_message('info', f"[FARM] Delete Farm request - Farm ID: {farm_id} - User: {session.get('username')}")
    
    db = get_db()
    lands = list(db.lands.find())
    
    for land in lands:
        farms = land.get('farms', [])
        for i, farm in enumerate(farms):
            if farm['_id'] == farm_id:
                farm_name = farm['name']
                farms.pop(i)
                db.lands.update_one({'_id': land['_id']}, {'$set': {'farms': farms}})
                log_message('info', f"Deleted farm: {farm_name}", session.get('user_id'), session.get('username'))
                flash('Farm deleted successfully!', 'success')
                return redirect(url_for('farms.index'))
    
    flash('Farm not found', 'danger')
    return redirect(url_for('farms.index'))


@log_func_call
@admin_required
@farms_bp.route('/bulk_add', methods=['POST'])
def bulk_add():
    log_message('info', f"Bulk Add Farm - Method {request.method} | {session.get('username')}")
    
    db = get_db()
    land_id = request.form.get('land_id')
    
    prefix = request.form.get('prefix', 'Farm').strip()
    start_from = request.form.get('start_from', 1)
    end_at = request.form.get('end_at', 5)
    
    try:
        start_from = int(start_from)
        end_at = int(end_at)
    except:
        start_from = 1
        end_at = 5
    
    names = [f"{prefix} {i}" for i in range(start_from, end_at + 1)]
    
    description = request.form.get('description', '')
    area_value = request.form.get('area', 0)
    area_unit = request.form.get('area_unit', 'ha')
    soil_type = request.form.get('soil_type', 'loam')
    topography = request.form.get('topography', '')
    climate_zone = request.form.get('climate_zone', '')
    
    lands = list(db.lands.find())
    for land in lands:
        if str(land['_id']) == land_id:
            if 'farms' not in land:
                land['farms'] = []
            added_count = 0
            for idx, name in enumerate(names):
                try:
                    farm_data = FarmModel(
                        # farm_number=start_from + idx,
                        name=name,
                        description=description,
                        location={
                            'area': {'value': float(area_value) or 0, 'unit': area_unit},
                            'soil_type': soil_type,
                            'topography': topography,
                            'climate_zone': climate_zone
                        },
                        metadata={
                            'status': 'active',
                            'notes': ''
                        }
                    )
                    farm_dict = farm_data.model_dump()
                    farm_dict['_id'] = str(ObjectId())
                    farm_dict['sectors'] = []
                    land['farms'].append(farm_dict)
                    added_count += 1
                except Exception as e:
                    flash(f'Validation error for "{name}": {str(e)}', 'danger')
            if added_count > 0:
                db.lands.update_one({'_id': land['_id']}, {'$set': {'farms': land.get('farms', [])}})
                log_message('info', f'Bulk added {added_count} farms', session.get('user_id'), session.get('username'))
                flash(f'{added_count} farms added successfully!', 'success')
            break
    
    return redirect(url_for('farms.index'))