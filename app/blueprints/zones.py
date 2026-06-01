import sys
import traceback
import json
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort
from app.database import get_db
from app.utils.logging import log_message, log_func_call
from app.models.validation import ZoneModel
from bson import ObjectId
from datetime import datetime

zones_bp = Blueprint('zones', __name__, url_prefix='/zones')
zones_bp.strict_slashes = False


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
@zones_bp.route('/')
def index():
    try:
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return render_template('zones/index.html', zones=[], sectors=[], search='')
        search = request.args.get('search', '').strip()
        lands = list(db.lands.find())
        zones = []
        sectors = []
        
        for land in lands:
            land['_id'] = str(land['_id'])
            for farm in land.get('farms', []):
                for sector in farm.get('sectors', []):
                    sector['_id'] = str(sector['_id'])
                    sector['land'] = land
                    sector['farm'] = farm
                    sectors.append(sector)
                    for zone in sector.get('zones', []):
                        if search and search.lower() not in zone.get('name', '').lower():
                            continue
                        zone['_id'] = str(zone.get('_id', ''))
                        zone['sector'] = sector
                        zone['sector_id'] = sector['_id']
                        zone['row_count'] = len(zone.get('rows', []))
                        zones.append(zone)
        
        return render_template('zones/index.html', zones=zones, sectors=sectors, search=search)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"zones.index() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error: {err["message"]}', 'danger')
        return render_template('zones/index.html', zones=[], sectors=[], search='')


@log_func_call
@zones_bp.route('/add', methods=['POST'])
def add():
    try:
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('lands.index'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('sectors.index'))
        sector_id = request.form.get('sector_id')
        land_id = request.form.get('land_id')
        
        try:
            def safe_float(value, default=0.0):
                try:
                    return float(value or default)
                except (ValueError, TypeError):
                    return default
            
            def safe_int(value, default=0):
                try:
                    return int(value or default)
                except (ValueError, TypeError):
                    return default
            
            pollinators_str = request.form.get('pollinators', '')
            pollinators = [p.strip() for p in pollinators_str.split(',') if p.strip()] if pollinators_str else []
            
            boundary = {'type': 'Polygon', 'coordinates': []}
            boundary_str = request.form.get('boundary', '').strip()
            if boundary_str:
                try:
                    boundary = json.loads(boundary_str)
                except:
                    pass
            
            zone_id_val = request.form.get('zone_id', '').strip()
            zone_number = request.form.get('zone_number', '')
            
            zone_data = ZoneModel(
                zone_id=zone_id_val,
                zone_number=zone_number,
                name=request.form.get('name', ''),
                description=request.form.get('description', ''),
                location={
                    'area': {'value': safe_float(request.form.get('area_value'), 0), 'unit': request.form.get('area_unit', 'ha')},
                    'row_spacing': {'value': safe_float(request.form.get('row_spacing_value'), 0), 'unit': request.form.get('row_spacing_unit', 'feet')},
                    'tree_spacing': {'value': safe_float(request.form.get('tree_spacing_value'), 0), 'unit': request.form.get('tree_spacing_unit', 'feet')},
                    'orientation': request.form.get('orientation', '')
                },
                boundary=boundary,
                crop_info={
                    'current_crop': request.form.get('current_crop', ''),
                    'variety': request.form.get('variety', ''),
                    'planting_date': request.form.get('planting_date', ''),
                    'root_stock': request.form.get('root_stock', ''),
                    'pollinators': pollinators
                },
                soil_characteristics={
                    'type': request.form.get('soil_type', ''),
                    'ph': safe_float(request.form.get('ph'), 0.0),
                    'organic_matter': request.form.get('organic_matter', ''),
                    'drainage': request.form.get('drainage', '')
                },
                statistics={
                    'total_rows': safe_int(request.form.get('total_rows'), 0),
                    'total_trees': safe_int(request.form.get('total_trees'), 0),
                    'trees_per_acre': safe_int(request.form.get('trees_per_acre'), 0),
                    'active_trees': safe_int(request.form.get('active_trees'), 0),
                    'dead_trees': safe_int(request.form.get('dead_trees'), 0),
                    'replacement_rate': request.form.get('replacement_rate', '')
                },
                maintenance={
                    'last_pruned': request.form.get('last_pruned', ''),
                    'last_fertilized': request.form.get('last_fertilized', ''),
                    'last_irrigated': request.form.get('last_irrigated', ''),
                    'next_maintenance': request.form.get('next_maintenance', ''),
                    'maintenance_notes': request.form.get('maintenance_notes', '')
                },
                metadata={
                    'created_date': request.form.get('created_date', ''),
                    'last_updated': request.form.get('last_updated', ''),
                    'status': request.form.get('status', 'active'),
                    'notes': request.form.get('notes', ''),
                    'zone_manager': request.form.get('zone_manager', '')
                }
            )
            
            zone_dict = zone_data.model_dump()
            zone_dict['_id'] = str(ObjectId())
            zone_dict['rows'] = []
            
            lands = list(db.lands.find())
            for land in lands:
                for farm in land.get('farms', []):
                    for sector in farm.get('sectors', []):
                        if str(sector.get('_id', '')) == sector_id:
                            if 'zones' not in sector:
                                sector['zones'] = []
                            sector['zones'].append(zone_dict)
                            db.lands.update_one(
                                {'_id': land['_id']},
                                {'$set': {'farms': land.get('farms', []), 'last_updated_at': datetime.now().isoformat()}}
                            )
                            log_message('info', f"Added zone: {zone_data.name}", session.get('user_id'), session.get('username'))
                            flash('Zone added successfully!', 'success')
                            return redirect(url_for('sectors.index'))
        except Exception as ve:
            flash(f'Validation error: {str(ve)}', 'danger')
        
        return redirect(url_for('zones.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"zones.add() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error adding zone: {err["message"]}', 'danger')
        return redirect(url_for('zones.index'))


@log_func_call
@zones_bp.route('/<zone_id>')
def detail(zone_id):
    try:
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            abort(500)
        lands = list(db.lands.find())
        
        for land in lands:
            land['_id'] = str(land['_id'])
            for farm in land.get('farms', []):
                for sector in farm.get('sectors', []):
                    sector['_id'] = str(sector['_id'])
                    for zone in sector.get('zones', []):
                        if str(zone.get('_id', '')) == zone_id:
                            zone['_id'] = str(zone['_id'])
                            zone['row_count'] = len(zone.get('rows', []))
                            
                            for row in zone.get('rows', []):
                                row['_id'] = str(row.get('_id', ''))
                                row['tree_count'] = len(row.get('trees', []))
                            
                            return render_template('zones/detail.html', zone=zone, sector=sector, land=land, rows=zone.get('rows', []))
        
        abort(404)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"zones.detail() line {err['line']}: {err['message']}\n{err['trace']}")
        abort(500)


@log_func_call
@zones_bp.route('/<zone_id>/edit', methods=['POST'])
def edit(zone_id):
    try:
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('lands.index'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('zones.index'))
        
        try:
            def safe_float(value, default=0.0):
                try:
                    return float(value or default)
                except (ValueError, TypeError):
                    return default
            
            def safe_int(value, default=0):
                try:
                    return int(value or default)
                except (ValueError, TypeError):
                    return default
            
            pollinators_str = request.form.get('pollinators', '')
            pollinators = [p.strip() for p in pollinators_str.split(',') if p.strip()] if pollinators_str else []
            
            boundary = {'type': 'Polygon', 'coordinates': []}
            boundary_str = request.form.get('boundary', '').strip()
            if boundary_str:
                try:
                    boundary = json.loads(boundary_str)
                except:
                    pass
            
            zone_id_val = request.form.get('zone_id', '').strip()
            zone_number = request.form.get('zone_number', '')
            
            zone_data = ZoneModel(
                zone_id=zone_id_val,
                zone_number=zone_number,
                name=request.form.get('name', ''),
                description=request.form.get('description', ''),
                location={
                    'area': {'value': safe_float(request.form.get('area_value')), 'unit': request.form.get('area_unit', 'ha')},
                    'row_spacing': {'value': safe_float(request.form.get('row_spacing_value')), 'unit': request.form.get('row_spacing_unit', 'feet')},
                    'tree_spacing': {'value': safe_float(request.form.get('tree_spacing_value')), 'unit': request.form.get('tree_spacing_unit', 'feet')},
                    'orientation': request.form.get('orientation', '')
                },
                boundary=boundary,
                crop_info={
                    'current_crop': request.form.get('current_crop', ''),
                    'variety': request.form.get('variety', ''),
                    'planting_date': request.form.get('planting_date', ''),
                    'root_stock': request.form.get('root_stock', ''),
                    'pollinators': pollinators
                },
                soil_characteristics={
                    'type': request.form.get('soil_type', ''),
                    'ph': safe_float(request.form.get('ph'), 0.0),
                    'organic_matter': request.form.get('organic_matter', ''),
                    'drainage': request.form.get('drainage', '')
                },
                statistics={
                    'total_rows': safe_int(request.form.get('total_rows')),
                    'total_trees': safe_int(request.form.get('total_trees')),
                    'trees_per_acre': safe_int(request.form.get('trees_per_acre')),
                    'active_trees': safe_int(request.form.get('active_trees')),
                    'dead_trees': safe_int(request.form.get('dead_trees')),
                    'replacement_rate': request.form.get('replacement_rate', '')
                },
                maintenance={
                    'last_pruned': request.form.get('last_pruned', ''),
                    'last_fertilized': request.form.get('last_fertilized', ''),
                    'last_irrigated': request.form.get('last_irrigated', ''),
                    'next_maintenance': request.form.get('next_maintenance', ''),
                    'maintenance_notes': request.form.get('maintenance_notes', '')
                },
                metadata={
                    'created_date': request.form.get('created_date', ''),
                    'last_updated': request.form.get('last_updated', ''),
                    'status': request.form.get('status', 'active'),
                    'notes': request.form.get('notes', ''),
                    'zone_manager': request.form.get('zone_manager', '')
                }
            )
            
            lands = list(db.lands.find())
            for land in lands:
                for farm in land.get('farms', []):
                    for sector in farm.get('sectors', []):
                        for zone in sector.get('zones', []):
                            if str(zone.get('_id', '')) == zone_id:
                                zone['zone_id'] = zone_data.zone_id
                                zone['zone_number'] = zone_data.zone_number
                                zone['name'] = zone_data.name
                                zone['description'] = zone_data.description
                                zone['location'] = zone_data.location
                                zone['boundary'] = zone_data.boundary
                                zone['crop_info'] = zone_data.crop_info
                                zone['soil_characteristics'] = zone_data.soil_characteristics
                                zone['statistics'] = zone_data.statistics
                                zone['maintenance'] = zone_data.maintenance
                                zone['metadata'] = zone_data.metadata
                                
                                db.lands.update_one({'_id': land['_id']}, {'$set': {'farms': land.get('farms', []), 'last_updated_at': datetime.now().isoformat()}})
                                log_message('info', f"Updated zone: {zone_data.name}", session.get('user_id'), session.get('username'))
                                flash('Zone updated successfully!', 'success')
                                return redirect(url_for('zones.index'))
        except Exception as ve:
            flash(f'Validation error: {str(ve)}', 'danger')
        
        return redirect(url_for('zones.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"zones.edit() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error updating zone: {err["message"]}', 'danger')
        return redirect(url_for('zones.index'))


@log_func_call
@zones_bp.route('/bulk_add', methods=['POST'])
def bulk_add():
    try:
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('lands.index'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('zones.index'))
        sector_id = request.form.get('sector_id')
        
        prefix = request.form.get('prefix', 'Zone').strip()
        start_from = request.form.get('start_from', 1)
        end_at = request.form.get('end_at', 5)
        
        try:
            start_from = int(start_from)
            end_at = int(end_at)
        except:
            start_from = 1
            end_at = 5
        
        names = [f"{prefix} {i}" for i in range(start_from, end_at + 1)]
        
        lands = list(db.lands.find())
        for land in lands:
            for farm in land.get('farms', []):
                for sector in farm.get('sectors', []):
                    if str(sector.get('_id', '')) == sector_id:
                        if 'zones' not in sector:
                            sector['zones'] = []
                        
                        added_count = 0
                        for idx, name in enumerate(names):
                            try:
                                zone_data = ZoneModel(
                                    zone_number=f"Z{idx+1:02d}",
                                    name=name,
                                    description='',
                                    location={
                                        'area': {'value': 0, 'unit': 'ha'},
                                        'row_spacing': {'value': 0, 'unit': 'feet'},
                                        'tree_spacing': {'value': 0, 'unit': 'feet'},
                                        'orientation': ''
                                    },
                                    boundary={'type': 'Polygon', 'coordinates': []},
                                    crop_info={'current_crop': '', 'variety': '', 'planting_date': '', 'root_stock': '', 'pollinators': []},
                                    soil_characteristics={'type': '', 'ph': 0.0, 'organic_matter': '', 'drainage': ''},
                                    statistics={'total_rows': 0, 'total_trees': 0, 'trees_per_acre': 0, 'active_trees': 0, 'dead_trees': 0, 'replacement_rate': ''},
                                    maintenance={'last_pruned': '', 'last_fertilized': '', 'last_irrigated': '', 'next_maintenance': '', 'maintenance_notes': ''},
                                    metadata={'created_date': '', 'last_updated': '', 'status': 'active', 'notes': '', 'zone_manager': ''}
                                )
                                
                                zone_dict = zone_data.model_dump()
                                zone_dict['_id'] = str(ObjectId())
                                zone_dict['rows'] = []
                                
                                sector['zones'].append(zone_dict)
                                added_count += 1
                            except Exception as ve:
                                flash(f'Validation error for "{name}": {str(ve)}', 'danger')
                        
                        if added_count > 0:
                            db.lands.update_one({'_id': land['_id']}, {'$set': {'farms': land.get('farms', []), 'last_updated_at': datetime.now().isoformat()}})
                            log_message('info', f'Bulk added {added_count} zones', session.get('user_id'), session.get('username'))
                            flash(f'{added_count} zones added successfully!', 'success')
                        break
        
        return redirect(url_for('zones.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"zones.bulk_add() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error bulk adding zones: {err["message"]}', 'danger')
        return redirect(url_for('zones.index'))
