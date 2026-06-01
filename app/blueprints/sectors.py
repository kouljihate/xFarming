import sys
import traceback
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort, jsonify
from app.database import get_db
from app.utils.logging import log_message, log_func_call
from app.utils.calculation import convert_and_calculate
from app.utils.map_utils import build_lands_map
from app.models.validation import SectorModel
from bson import ObjectId
from datetime import datetime
import json

sectors_bp = Blueprint('sectors', __name__, url_prefix='/sectors')
sectors_bp.strict_slashes = False


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
@sectors_bp.route('/')
def index():
    try:
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return render_template('sectors/index.html', sectors=[], lands=[], search='', lands_farms_json='{}', map_html=None)
        search = request.args.get('search', '').strip()
        lands = list(db.lands.find())
        sectors = []
        lands_for_select = []
        
        for land in lands:
            land['_id'] = str(land['_id'])
            lands_for_select.append(land)
            for farm in land.get('farms', []):
                for sector in farm.get('sectors', []):
                    sector['_id'] = str(sector.get('_id', ''))
                    if search and search.lower() not in sector.get('name', '').lower():
                        continue
                    sector['land'] = land
                    sector['farm'] = farm
                    sector['land_id'] = land['_id']
                    sector['zone_count'] = len(sector.get('zones', []))
                    sectors.append(sector)
        
        lands_farms = {}
        for land in lands_for_select:
            lands_farms[land['_id']] = [{
                '_id': str(farm.get('_id', '')),
                'farm_name': farm.get('farm_name', farm.get('name', ''))
            } for farm in land.get('farms', [])]

        map_html = build_lands_map(lands_for_select, height=400)
        return render_template('sectors/index.html', sectors=sectors, lands=lands_for_select, search=search, lands_farms_json=json.dumps(lands_farms), map_html=map_html)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"sectors.index() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error: {err["message"]}', 'danger')
        return render_template('sectors/index.html', sectors=[], lands=[], search='', lands_farms_json='{}', map_html=None)


@log_func_call
@sectors_bp.route('/calculate', methods=['POST'])
def calculate():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        coords = request.form.get('coordinates', '').strip()
        result = convert_and_calculate(coords)
        
        if isinstance(result, dict) and result.get('error'):
            flash(result['message'] if 'message' in result else result['error'], 'danger')
            return redirect(url_for('sectors.index'))
        
        if 'error' in result:
            flash(result['error'], 'danger')
            return redirect(url_for('sectors.index'))
        
        lands = list(get_db().lands.find())
        lands_farms = {}
        for land in lands:
            land['_id'] = str(land['_id'])
            lands_farms[land['_id']] = [{
                '_id': str(farm.get('_id', '')),
                'farm_name': farm.get('farm_name', farm.get('name', ''))
            } for farm in land.get('farms', [])]

        return render_template('sectors/index.html', 
                               lands=lands,
                               calc_area=result['area'],
                               calc_perimeter=result['perimeter'],
                               calc_geojson=result['geojson'],
                               calc_coords=coords,
                               lands_farms_json=json.dumps(lands_farms),
                               map_html=build_lands_map(lands, height=400))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"sectors.calculate() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Calculation error: {err["message"]}', 'danger')
        return redirect(url_for('sectors.index'))


@log_func_call
@sectors_bp.route('/add', methods=['POST'])
def add():
    try:
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('lands.index'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('sectors.index'))
        land_id = request.form.get('land_id')
        farm_id = request.form.get('farm_id', '')
        
        try:
            sector_id = request.form.get('sector_id', '').strip()
            sector_number = request.form.get('sector_number', 1)
            try:
                sector_number = int(sector_number)
            except:
                sector_number = 1
            
            sector_data = SectorModel(
                sector_id=sector_id,
                sector_number=sector_number,
                name=request.form.get('name', ''),
                description=request.form.get('description', ''),
                location={
                    'area': {'value': float(request.form.get('area', 0) or 0), 'unit': request.form.get('area_unit', 'ha')},
                    'soil_type': request.form.get('soil_type', 'loam'),
                    'slope': request.form.get('slope', ''),
                    'irrigation_type': request.form.get('irrigation_type', '')
                },
                metadata={
                    'status': 'active',
                    'notes': request.form.get('notes', '')
                }
            )
            
            if not farm_id:
                flash('Farm is required to add a sector', 'danger')
                return redirect(url_for('sectors.index'))
            lands = list(db.lands.find())
            for land in lands:
                if str(land['_id']) == land_id:
                    sector_dict = sector_data.model_dump()
                    sector_dict['_id'] = str(ObjectId())
                    sector_dict['zones'] = []
                    sector_dict['farm_id'] = farm_id
                    
                    db.lands.update_one(
                        {'_id': land['_id'], 'farms._id': farm_id},
                        {'$push': {'farms.$.sectors': sector_dict}, '$set': {'last_updated_at': datetime.now().isoformat()}}
                    )
                    log_message('info', f"Added sector: {sector_data.name}", session.get('user_id'), session.get('username'))
                    flash('Sector added successfully!', 'success')
                    break
        except Exception as ve:
            flash(f'Validation error: {str(ve)}', 'danger')
        
        return redirect(url_for('sectors.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"sectors.add() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error adding sector: {err["message"]}', 'danger')
        return redirect(url_for('sectors.index'))


@log_func_call
@sectors_bp.route('/<sector_id>')
def detail(sector_id):
    try:
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            abort(500)
        lands = list(db.lands.find())
        
        for land in lands:
            for farm in land.get('farms', []):
                for sector in farm.get('sectors', []):
                    if str(sector.get('_id', '')) == sector_id:
                        sector['land'] = land
                        sector['farm'] = farm
                        sector['_id'] = str(sector['_id'])
                        
                        for zone in sector.get('zones', []):
                            zone['_id'] = str(zone.get('_id', ''))
                            zone['row_count'] = len(zone.get('rows', []))
                            for row in zone.get('rows', []):
                                row['_id'] = str(row.get('_id', ''))
                                row['tree_count'] = len(row.get('trees', []))
                        
                        return render_template('sectors/detail.html', sector=sector, land=land, zones=sector.get('zones', []))
        
        abort(404)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"sectors.detail() line {err['line']}: {err['message']}\n{err['trace']}")
        abort(500)


@log_func_call
@sectors_bp.route('/<sector_id>/edit', methods=['GET', 'POST'])
def edit(sector_id):
    try:
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('lands.index'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('sectors.index'))
        lands = list(db.lands.find())
        
        for land in lands:
            for farm in land.get('farms', []):
                for sector in farm.get('sectors', []):
                    if str(sector.get('_id', '')) == sector_id:
                        if request.method == 'POST':
                            try:
                                boundary = None
                                boundary_str = request.form.get('boundary', '').strip()
                                if boundary_str:
                                    try:
                                        boundary = json.loads(boundary_str)
                                    except:
                                        boundary = sector.get('boundary', {'type': 'Polygon', 'coordinates': []})
                                else:
                                    boundary = sector.get('boundary', {'type': 'Polygon', 'coordinates': []})
                                
                                sector_id_val = request.form.get('sector_id', '').strip()
                                sector_number = request.form.get('sector_number', sector.get('sector_number', 1))
                                try:
                                    sector_number = int(sector_number)
                                except:
                                    sector_number = 1
                                
                                sector_data = SectorModel(
                                    sector_id=sector_id_val,
                                    sector_number=sector_number,
                                    name=request.form.get('name', ''),
                                    description=request.form.get('description', ''),
                                    location={
                                        'area': {'value': float(request.form.get('area', 0) or 0), 'unit': request.form.get('area_unit', 'ha')},
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
                                
                                sector['sector_id'] = sector_data.sector_id
                                sector['sector_number'] = sector_data.sector_number
                                sector['name'] = sector_data.name
                                sector['description'] = sector_data.description
                                sector['location'] = sector_data.location
                                sector['boundary'] = sector_data.boundary
                                sector['metadata'] = sector_data.metadata
                                
                                db.lands.update_one({'_id': land['_id']}, {'$set': {'farms': land.get('farms', []), 'last_updated_at': datetime.now().isoformat()}})
                                log_message('info', f"Updated sector: {sector_data.name}", session.get('user_id'), session.get('username'))
                                flash('Sector updated successfully!', 'success')
                            except Exception as ve:
                                flash(f'Validation error: {str(ve)}', 'danger')
                            return redirect(url_for('sectors.index'))
                        else:
                            return render_template('sectors/edit.html', sector=sector, land=land)
        
        abort(404)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"sectors.edit() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error editing sector: {err["message"]}', 'danger')
        return redirect(url_for('sectors.index'))


@log_func_call
@sectors_bp.route('/<sector_id>/delete', methods=['POST'])
def delete(sector_id):
    try:
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('lands.index'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('sectors.index'))
        lands = list(db.lands.find())
        
        for land in lands:
            for farm in land.get('farms', []):
                sectors = farm.get('sectors', [])
                for i, sector in enumerate(sectors):
                    if str(sector.get('_id', '')) == sector_id:
                        sector_name = sector.get('name', '')
                        sectors.pop(i)
                        db.lands.update_one({'_id': land['_id']}, {'$set': {'farms': land.get('farms', []), 'last_updated_at': datetime.now().isoformat()}})
                        log_message('info', f"Deleted sector: {sector_name}", session.get('user_id'), session.get('username'))
                        flash('Sector deleted successfully!', 'success')
                        return redirect(url_for('sectors.index'))
        
        flash('Sector not found', 'danger')
        return redirect(url_for('sectors.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"sectors.delete() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error deleting sector: {err["message"]}', 'danger')
        return redirect(url_for('sectors.index'))


@log_func_call
@sectors_bp.route('/bulk_add', methods=['POST'])
def bulk_add():
    try:
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('lands.index'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('sectors.index'))
        land_id = request.form.get('land_id')
        farm_id = request.form.get('farm_id', '')
        
        if not farm_id:
            flash('Farm is required to bulk add sectors', 'danger')
            return redirect(url_for('sectors.index'))
        
        prefix = request.form.get('prefix', 'Sector').strip()
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
        slope = request.form.get('slope', '')
        irrigation_type = request.form.get('irrigation_type', '')
        
        lands = list(db.lands.find())
        for land in lands:
            if str(land['_id']) == land_id:
                for farm in land.get('farms', []):
                    if str(farm.get('_id', '')) == farm_id:
                        if 'sectors' not in farm:
                            farm['sectors'] = []
                        added_count = 0
                        for idx, name in enumerate(names):
                            try:
                                sector_data = SectorModel(
                                    sector_number=start_from + idx,
                                    name=name,
                                    description=description,
                                    location={
                                        'area': {'value': float(area_value) or 0, 'unit': area_unit},
                                        'soil_type': soil_type,
                                        'slope': slope,
                                        'irrigation_type': irrigation_type
                                    },
                                    metadata={'status': 'active', 'notes': ''}
                                )
                                sector_dict = sector_data.model_dump()
                                sector_dict['_id'] = str(ObjectId())
                                sector_dict['zones'] = []
                                sector_dict['farm_id'] = farm_id
                                farm['sectors'].append(sector_dict)
                                added_count += 1
                            except Exception as ve:
                                flash(f'Validation error for "{name}": {str(ve)}', 'danger')
                        if added_count > 0:
                            db.lands.update_one({'_id': land['_id']}, {'$set': {'farms': land.get('farms', []), 'last_updated_at': datetime.now().isoformat()}})
                            log_message('info', f'Bulk added {added_count} sectors', session.get('user_id'), session.get('username'))
                            flash(f'{added_count} sectors added successfully!', 'success')
                        break
                break
        
        return redirect(url_for('sectors.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"sectors.bulk_add() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error bulk adding sectors: {err["message"]}', 'danger')
        return redirect(url_for('sectors.index'))
