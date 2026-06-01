import sys
import traceback
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort, jsonify
from app.database import get_db
from app.utils.logging import log_message, log_func_call, login_required, admin_required
from app.utils.calculation import convert_and_calculate, calculate_centroid, calculate_polygon_metrics, parse_simple_coordinates
from app.utils.map_utils import build_lands_map, build_land_detail_map
from app.models.validation import FarmModel
from bson import ObjectId
from datetime import datetime
from app.utils.map_browsing import generate_map


farms_bp = Blueprint('farms', __name__, url_prefix='/farms')
farms_bp.strict_slashes = False


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
@login_required
@farms_bp.route('/')
def index():
    try:
        log_message('info', f"[FARM] Index page - User: {session.get('username')}")
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return render_template('farms/index.html', farms=[], lands=[], search='', form_data={})
        search = request.args.get('search', '').strip()
        lands = [land for land in db.lands.find() if land is not None]
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
                if search and search.lower() not in farm.get('farm_name', '').lower():
                    continue
                farm['land'] = land
                farm['land_id'] = land['_id']
                farm['sector_count'] = len(farm.get('sectors', []))
                farms.append(farm)
        
        return render_template('farms/index.html', farms=farms, lands=lands_for_select, search=search, form_data={})
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"farms.index() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error: {err["message"]}', 'danger')
        return render_template('farms/index.html', farms=[], lands=[], search='', form_data={})


@log_func_call
@login_required
@farms_bp.route('/calculate', methods=['POST'])
def calculate():
    try:
        log_message('info', f"Calculate Farm - Method {request.method} | {session.get('username')}")
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('farms.index'))
        
        coords = request.form.get('coordinates', '').strip()
        result = convert_and_calculate(coords)
        
        if isinstance(result, dict) and result.get('error'):
            flash(result.get('message', result.get('error', 'Calculation failed')), 'danger')
            return redirect(url_for('farms.index'))
        
        if 'error' in result:
            flash(result['error'], 'danger')
            return redirect(url_for('farms.index'))
        
        return render_template('farms/index.html', 
                               lands=list(db.lands.find()),
                               calc_area=result.get('area_ha'),
                               calc_perimeter=result.get('perimeter_m'),
                               calc_geojson=result.get('geojson', ''),
                               calc_coords=coords)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"farms.calculate() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Calculation error: {err["message"]}', 'danger')
        return redirect(url_for('farms.index'))


@log_func_call
@admin_required
@farms_bp.route('/add', methods=['POST'])
def add():
    try:
        form_data = request.form.to_dict()
        
        action = form_data.get("action")

        if action == "calculate":
            log_message('info', f"[FARM] Calculate")
            try:
                coords = request.form.get('coordinates', '').strip()
                coords = parse_simple_coordinates(coords)
                if coords is None:
                    flash('Invalid coordinates. Please enter at least 3 coordinate pairs.', 'danger')
                    db = get_db()
                    lands = list(db.lands.find()) if not (isinstance(db, dict) and db.get('error')) else []
                    for land in lands:
                        land['_id'] = str(land['_id'])
                    return render_template('farms/index.html', farms=[], lands=lands, show_add_modal=True, form_data=request.form.to_dict(flat=True))
                result_polygon = calculate_polygon_metrics(coords)
                result_centroid = calculate_centroid(coords)
                
                if (isinstance(result_polygon, dict) and result_polygon.get('error')) or \
                   (isinstance(result_centroid, dict) and result_centroid.get('error')):
                    err_msg = (result_polygon.get('message', result_polygon.get('error'))
                               if isinstance(result_polygon, dict) and result_polygon.get('error')
                               else result_centroid.get('message', result_centroid.get('error')))
                    log_message('error', f"[FARM] Calculate Farm Error: {err_msg}")
                    flash(err_msg, 'danger')
                    db = get_db()
                    lands = list(db.lands.find()) if not (isinstance(db, dict) and db.get('error')) else []
                    for land in lands:
                        land['_id'] = str(land['_id'])
                    return render_template('farms/index.html', farms=[], lands=lands, show_add_modal=True, form_data=request.form.to_dict(flat=True))
                
                db = get_db()
                lands = list(db.lands.find()) if not (isinstance(db, dict) and db.get('error')) else []
                for land in lands:
                    land['_id'] = str(land['_id'])
                
                return render_template('farms/index.html', 
                                       lands=lands,
                                       calc_area=result_polygon.get('area_ha'),
                                       calc_perimeter=result_polygon.get('perimeter_m'),
                                       calc_center_lat=result_centroid.get('latitude'),
                                       calc_center_lon=result_centroid.get('longitude'),
                                       calc_coords=coords,
                                       calc_geojson=result_polygon.get('geojson', ''),
                                       google_map_url=result_centroid.get('maps_url', ''),
                                       show_add_modal=True,
                                       form_data=request.form.to_dict(flat=True),
                                       active_tab='')
            except Exception as calc_err:
                err = _error_info(calc_err)
                log_message('error', f"[FARM] Calculate action failed line {err['line']}: {err['message']}")
                flash(f'Calculation error: {err["message"]}', 'danger')
                return redirect(url_for('farms.index'))

        if action == "show_map":
            try:
                generate_map(
                    result_centroid,
                    label=f"Farm Parcel - {request.form.get('name', '')}",
                    output_path="map.html",
                    open_browser=True,
                )

                db = get_db()
                lands = list(db.lands.find()) if not (isinstance(db, dict) and db.get('error')) else []
                for land in lands:
                    land['_id'] = str(land['_id'])
                return render_template('farms/index.html',
                                       farms=[],
                                       lands=lands,
                                       show_add_modal=True,
                                       form_data=request.form.to_dict(flat=True),
                                       active_tab='')
            except Exception as map_err:
                err = _error_info(map_err)
                log_message('error', f"[FARM] Show map failed line {err['line']}: {err['message']}")
                flash(f'Map error: {err["message"]}', 'danger')
                return redirect(url_for('farms.index'))

        if action == "save":
            try:
                log_message('info', f"[FARM] Add Farm Form Data: {action} \n {form_data}")

                farm_data = FarmModel(
                    farm_id = form_data.get("farm_id"),
                    farm_name = form_data.get("farm_name"),
                    description = form_data.get("description"),
                    boundary = form_data.get("boundary"),
                    location = form_data.get("location"),
                    irrigation_system = form_data.get("irrigation_system"),
                    legal = form_data.get("legal"),
                    photos = form_data.get("photos"),
                    metadata = form_data.get("metadata"),
                )

                farm_dict = farm_data.model_dump()
                farm_dict['_id'] = str(ObjectId())
                farm_dict['sectors'] = []
                    
                db = get_db()
                if isinstance(db, dict) and db.get('error'):
                    flash(f'Database error: {db["message"]}', 'danger')
                    return redirect(url_for('lands.index'))
                db.lands.update_one(
                    {'_id': ObjectId(request.form.get('land_id', ''))},
                    {
                        '$push': {
                            'farms': farm_dict
                        },
                        '$set': {'last_updated_at': datetime.now().isoformat()}
                    }
                )

                log_message('info', f"[FARM] Added farm: {farm_data.farm_name}", session.get('user_id'), session.get('username'))
                flash('Farm added successfully!', 'success')
                return redirect(url_for('lands.index'))

            except Exception as e:
                log_message('error', f"[FARM] Add Farm failed - User: {session.get('username')} - Error: {str(e)}")
                flash(f'Validation error: {str(e)}', 'danger')
                return redirect(url_for('lands.index'))
        
        flash('Unknown action', 'danger')
        return redirect(url_for('farms.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"farms.add() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error: {err["message"]}', 'danger')
        return redirect(url_for('farms.index'))


@log_func_call
@login_required
@farms_bp.route('/<farm_id>')
def detail(farm_id):
    try:
        log_message('info', f"Detail Farm {farm_id} - Method {request.method} | {session.get('username')}")
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            abort(500)
        lands = list(db.lands.find())
        
        for land in lands:
            for farm in land.get('farms', []):
                if str(farm.get('_id', '')) == farm_id:
                    farm['land'] = land
                    farm['_id'] = str(farm['_id'])
                    
                    sectors = farm.get('sectors', [])
                    for sector in sectors:
                        sector['_id'] = str(sector.get('_id', ''))
                        sector['zone_count'] = len(sector.get('zones', []))
                        for zone in sector.get('zones', []):
                            zone['_id'] = str(zone.get('_id', ''))
                            zone['row_count'] = len(zone.get('rows', []))
                            for row in zone.get('rows', []):
                                row['_id'] = str(row.get('_id', ''))
                                row['tree_count'] = len(row.get('trees', []))
                    
                    map_html = build_land_detail_map(land, height=400)
                    return render_template('farms/detail.html', farm=farm, land=land, sectors=sectors, map_html=map_html)
        
        abort(404)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"farms.detail() line {err['line']}: {err['message']}\n{err['trace']}")
        abort(500)


@log_func_call
@admin_required
@farms_bp.route('/<farm_id>/edit', methods=['GET', 'POST'])
def edit(farm_id):
    try:
        if request.method == 'GET':
            log_message('info', f"[FARM] Edit Farm modal opened - Farm ID: {farm_id} - User: {session.get('username')}")
        else:
            log_message('info', f"[FARM] Edit Farm form submitted - Farm ID: {farm_id} - User: {session.get('username')}")
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('farms.index'))
        lands = list(db.lands.find())
        
        for land in lands:
            for farm in land.get('farms', []):
                if str(farm.get('_id', '')) == farm_id:
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
                            try:
                                farm_id_val = int(farm_id_val)
                            except:
                                farm_id_val = 1
                            
                            farm_data = FarmModel(
                                farm_id=str(farm_id_val),
                                farm_name=request.form.get('farm_name', ''),
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
                            farm['farm_name'] = farm_data.farm_name
                            farm['description'] = farm_data.description
                            farm['location'] = farm_data.location
                            farm['boundary'] = farm_data.boundary
                            farm['irrigation_system'] = farm_data.irrigation_system
                            farm['legal'] = farm_data.legal
                            farm['metadata'] = farm_data.metadata
                            
                            db.lands.update_one({'_id': land['_id']}, {'$set': {'farms': land.get('farms', []), 'last_updated_at': datetime.now().isoformat()}})
                            log_message('info', f"Updated farm: {farm_data.farm_name}", session.get('user_id'), session.get('username'))
                            flash('Farm updated successfully!', 'success')
                        except Exception as e:
                            flash(f'Validation error: {str(e)}', 'danger')
                        return redirect(url_for('farms.index'))
                    else:
                        return render_template('farms/edit.html', farm=farm, land=land)
        
        abort(404)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"farms.edit() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error editing farm: {err["message"]}', 'danger')
        return redirect(url_for('farms.index'))


@log_func_call
@admin_required
@farms_bp.route('/<farm_id>/delete', methods=['POST'])
def delete(farm_id):
    try:
        log_message('info', f"[FARM] Delete Farm request - Farm ID: {farm_id} - User: {session.get('username')}")
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('farms.index'))
        lands = list(db.lands.find())
        
        for land in lands:
            farms = land.get('farms', [])
            for i, farm in enumerate(farms):
                if str(farm.get('_id', '')) == farm_id:
                    farm_name = farm.get('farm_name', '')
                    farms.pop(i)
                    db.lands.update_one({'_id': land['_id']}, {'$set': {'farms': farms, 'last_updated_at': datetime.now().isoformat()}})
                    log_message('info', f"Deleted farm: {farm_name}", session.get('user_id'), session.get('username'))
                    flash('Farm deleted successfully!', 'success')
                    return redirect(url_for('farms.index'))
        
        flash('Farm not found', 'danger')
        return redirect(url_for('farms.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"farms.delete() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error deleting farm: {err["message"]}', 'danger')
        return redirect(url_for('farms.index'))


@log_func_call
@admin_required
@farms_bp.route('/bulk_add', methods=['POST'])
def bulk_add():
    try:
        log_message('info', f"Bulk Add Farm - Method {request.method} | {session.get('username')}")
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('farms.index'))
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
                            farm_name=name,
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
                    db.lands.update_one({'_id': land['_id']}, {'$set': {'farms': land.get('farms', []), 'last_updated_at': datetime.now().isoformat()}})
                    log_message('info', f'Bulk added {added_count} farms', session.get('user_id'), session.get('username'))
                    flash(f'{added_count} farms added successfully!', 'success')
                break
        
        return redirect(url_for('farms.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"farms.bulk_add() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error bulk adding farms: {err["message"]}', 'danger')
        return redirect(url_for('farms.index'))
