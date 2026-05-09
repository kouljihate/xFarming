from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort, jsonify
from app.database import get_db
from app.utils.logging import log_message
from app.utils.calculation import convert_and_calculate
from app.models.validation import FarmModel
from bson import ObjectId
from datetime import datetime

farms_bp = Blueprint('farms', __name__, url_prefix='/farms')
farms_bp.strict_slashes = False


@farms_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    search = request.args.get('search', '').strip()
    lands = list(db.lands.find())
    farms = []
    lands_for_select = []
    
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
    
    return render_template('farms/index.html', farms=farms, lands=lands_for_select, search=search)


@farms_bp.route('/calculate', methods=['POST'])
def calculate():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    coords = request.form.get('coordinates', '').strip()
    result = convert_and_calculate(coords)
    
    if 'error' in result:
        flash(result['error'], 'danger')
        return redirect(url_for('farms.index'))
    
    return render_template('farms/index.html', 
                           lands=list(get_db().lands.find()),
                           calc_area=result['area'],
                           calc_perimeter=result['perimeter'],
                           calc_geojson=result['geojson'],
                           calc_coords=coords)


@farms_bp.route('/add', methods=['POST'])
def add():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('farms.index'))
    
    if request.form.get('calculate'):
        coords = request.form.get('coordinates', '').strip()
        result = convert_and_calculate(coords)
        
        db = get_db()
        lands = list(db.lands.find())
        for land in lands:
            land['_id'] = str(land['_id'])
        
        if 'error' in result:
            flash(result['error'], 'danger')
            return render_template('farms/index.html', farms=[], lands=lands)
        
        return render_template('farms/index.html', 
                               farms=[],
                               lands=lands,
                               calc_area=result['area'],
                               calc_perimeter=result['perimeter'],
                               calc_geojson=result['geojson'],
                               calc_coords=coords,
                               show_add_modal=True,
                               active_tab='location')
    
    db = get_db()
    land_id = request.form.get('land_id')
    
    try:
        import json
        
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
        farm_number = request.form.get('farm_number', 1)
        try:
            farm_number = int(farm_number)
        except:
            farm_number = 1
        
        farm_data = FarmModel(
            farm_id=farm_id,
            farm_number=farm_number,
            name=request.form.get('name', ''),
            description=request.form.get('description', ''),
            location={
                'area': {'value': float(request.form.get('area', 0) or 0), 'unit': request.form.get('area_unit', 'acres')},
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
            metadata={
                'status': request.form.get('status', 'active'),
                'notes': request.form.get('notes', '')
            }
        )
        
        lands = list(db.lands.find())
        for land in lands:
            if str(land['_id']) == land_id:
                farm_dict = farm_data.model_dump()
                farm_dict['_id'] = str(ObjectId())
                farm_dict['sectors'] = []
                
                if 'farms' not in land:
                    land['farms'] = []
                land['farms'].append(farm_dict)
                db.lands.update_one({'_id': land['_id']}, {'$set': {'farms': land.get('farms', [])}})
                log_message('info', f"Added farm: {farm_data.name}", session.get('user_id'), session.get('username'))
                flash('Farm added successfully!', 'success')
                break
    except Exception as e:
        flash(f'Validation error: {str(e)}', 'danger')
    
    return redirect(url_for('farms.index'))


@farms_bp.route('/<farm_id>')
def detail(farm_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
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


@farms_bp.route('/<farm_id>/edit', methods=['GET', 'POST'])
def edit(farm_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('farms.index'))
    
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
                        
                        farm_id_val = request.form.get('farm_id', '').strip()
                        farm_number = request.form.get('farm_number', farm.get('farm_number', 1))
                        try:
                            farm_number = int(farm_number)
                        except:
                            farm_number = 1
                        
                        farm_data = FarmModel(
                            farm_id=farm_id_val,
                            farm_number=farm_number,
                            name=request.form.get('name', ''),
                            description=request.form.get('description', ''),
                            location={
                                'area': {'value': float(request.form.get('area', 0) or 0), 'unit': request.form.get('area_unit', 'acres')},
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
                            metadata={
                                'status': request.form.get('status', 'active'),
                                'notes': request.form.get('notes', '')
                            }
                        )
                        
                        farm['farm_id'] = farm_data.farm_id
                        farm['farm_number'] = farm_data.farm_number
                        farm['name'] = farm_data.name
                        farm['description'] = farm_data.description
                        farm['location'] = farm_data.location
                        farm['boundary'] = farm_data.boundary
                        farm['irrigation_system'] = farm_data.irrigation_system
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


@farms_bp.route('/<farm_id>/delete', methods=['POST'])
def delete(farm_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('farms.index'))
    
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


@farms_bp.route('/bulk_add', methods=['POST'])
def bulk_add():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('farms.index'))
    
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
    area_unit = request.form.get('area_unit', 'acres')
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
                        farm_number=start_from + idx,
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