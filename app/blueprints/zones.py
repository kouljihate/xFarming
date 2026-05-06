from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort
from app.database import get_db
from app.utils.logging import log_message
from app.models.validation import ZoneModel
from bson import ObjectId

zones_bp = Blueprint('zones', __name__, url_prefix='/zones')
zones_bp.strict_slashes = False

@zones_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    search = request.args.get('search', '').strip()
    lands = list(db.lands.find())
    zones = []
    sectors = []
    
    for land in lands:
        land['_id'] = str(land['_id'])
        for sector in land.get('sectors', []):
            sector['_id'] = str(sector['_id'])
            sector['land'] = land
            sectors.append(sector)
            for zone in sector.get('zones', []):
                if search and search.lower() not in zone['name'].lower():
                    continue
                zone['_id'] = str(zone['_id'])
                zone['sector'] = sector
                zone['sector_id'] = sector['_id']
                zone['row_count'] = len(zone.get('rows', []))
                zones.append(zone)
    
    return render_template('zones/index.html', zones=zones, sectors=sectors, search=search)

@zones_bp.route('/add', methods=['POST'])
def add():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    sector_id = request.form.get('sector_id')
    land_id = request.form.get('land_id')
    
    try:
        import json
        
        # Safe float conversion
        def safe_float(value, default=0.0):
            try:
                val = float(value or default)
                return val
            except (ValueError, TypeError):
                return default
        
        # Safe int conversion
        def safe_int(value, default=0):
            try:
                val = int(value or default)
                return val
            except (ValueError, TypeError):
                return default
        
        # Parse pollinators (comma-separated)
        pollinators_str = request.form.get('pollinators', '')
        pollinators = [p.strip() for p in pollinators_str.split(',') if p.strip()] if pollinators_str else []
        
        # Parse boundary if provided
        boundary = {'type': 'Polygon', 'coordinates': []}
        boundary_str = request.form.get('boundary', '').strip()
        if boundary_str:
            try:
                boundary = json.loads(boundary_str)
            except:
                pass
        
        # Get zone_id and zone_number
        zone_id = request.form.get('zone_id', '').strip()
        zone_number = request.form.get('zone_number', '')
        
        # Validate with ZoneModel
        zone_data = ZoneModel(
            zone_id=zone_id,
            zone_number=zone_number,
            name=request.form.get('name', ''),
            description=request.form.get('description', ''),
            location={
                'area': {'value': safe_float(request.form.get('area_value'), 0), 'unit': request.form.get('area_unit', 'acres')},
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
        
        lands = list(db.lands.find())
        for land in lands:
            for sector in land.get('sectors', []):
                if sector['_id'] == sector_id:
                    if 'zones' not in sector:
                        sector['zones'] = []
                    
                    zone_dict = zone_data.model_dump()
                    zone_dict['_id'] = str(ObjectId())
                    zone_dict['rows'] = []
                    
                    sector['zones'].append(zone_dict)
                    db.lands.update_one({'_id': land['_id']}, {'$set': {'sectors': land.get('sectors', [])}})
                    log_message('info', f"Added zone: {zone_data.name}", session.get('user_id'), session.get('username'))
                    flash('Zone added successfully!', 'success')
                    return redirect(url_for('sectors.index'))
    except Exception as e:
        flash(f'Validation error: {str(e)}', 'danger')
    
    return redirect(url_for('sectors.index'))

@zones_bp.route('/<zone_id>')
def detail(zone_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    lands = list(db.lands.find())
    
    for land in lands:
        land['_id'] = str(land['_id'])
        for sector in land.get('sectors', []):
            sector['_id'] = str(sector['_id'])
            for zone in sector.get('zones', []):
                if zone['_id'] == zone_id:
                    zone['_id'] = str(zone['_id'])
                    zone['row_count'] = len(zone.get('rows', []))
                    
                    for row in zone.get('rows', []):
                        row['_id'] = str(row['_id'])
                        row['tree_count'] = len(row.get('trees', []))
                    
                    return render_template('zones/detail.html', zone=zone, sector=sector, land=land, rows=zone.get('rows', []))
    
    abort(404)

@zones_bp.route('/<zone_id>/edit', methods=['POST'])
def edit(zone_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    
    try:
        import json
        
        # Safe float conversion
        def safe_float(value, default=0.0):
            try:
                val = float(value or default)
                return val
            except (ValueError, TypeError):
                return default
        
        # Safe int conversion
        def safe_int(value, default=0):
            try:
                val = int(value or default)
                return val
            except (ValueError, TypeError):
                return default
        
        # Parse pollinators (comma-separated)
        pollinators_str = request.form.get('pollinators', '')
        pollinators = [p.strip() for p in pollinators_str.split(',') if p.strip()] if pollinators_str else []
        
        # Parse boundary if provided
        boundary = zone.get('boundary', {'type': 'Polygon', 'coordinates': []})
        boundary_str = request.form.get('boundary', '').strip()
        if boundary_str:
            try:
                boundary = json.loads(boundary_str)
            except:
                pass
        
        # Get zone_id and zone_number
        zone_id_val = request.form.get('zone_id', '').strip()
        zone_number = request.form.get('zone_number', '')
        
        # Validate with ZoneModel
        zone_data = ZoneModel(
            zone_id=zone_id_val,
            zone_number=zone_number,
            name=request.form.get('name', ''),
            description=request.form.get('description', ''),
            location={
                'area': {'value': safe_float(request.form.get('area_value')), 'unit': request.form.get('area_unit', 'acres')},
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
            for sector in land.get('sectors', []):
                for zone in sector.get('zones', []):
                    if zone['_id'] == zone_id:
                        # Update zone with validated data
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
                        
                        db.lands.update_one({'_id': land['_id']}, {'$set': {'sectors': land.get('sectors', [])}})
                        log_message('info', f"Updated zone: {zone_data.name}", session.get('user_id'), session.get('username'))
                        flash('Zone updated successfully!', 'success')
                        return redirect(url_for('zones.index'))
    except Exception as e:
        flash(f'Validation error: {str(e)}', 'danger')
    
    return redirect(url_for('zones.index'))

@zones_bp.route('/bulk_add', methods=['POST'])
def bulk_add():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    sector_id = request.form.get('sector_id')
    
    try:
        import json
        
        # Safe float conversion
        def safe_float(value, default=0.0):
            try:
                val = float(value or default)
                return val
            except (ValueError, TypeError):
                return default
        
        # Safe int conversion
        def safe_int(value, default=0):
            try:
                val = int(value or default)
                return val
            except (ValueError, TypeError):
                return default
        
        # Parse names
        names = request.form.get('names', '').strip().split('\n')
        
        # Parse pollinators (comma-separated)
        pollinators_str = request.form.get('pollinators', '')
        pollinators = [p.strip() for p in pollinators_str.split(',') if p.strip()] if pollinators_str else []
        
        # Parse boundary if provided
        boundary = {'type': 'Polygon', 'coordinates': []}
        boundary_str = request.form.get('boundary', '').strip()
        if boundary_str:
            try:
                boundary = json.loads(boundary_str)
            except:
                pass
        
        # Get zone_id prefix and zone_number start
        zone_id_prefix = request.form.get('zone_id_prefix', '').strip()
        zone_number_start = request.form.get('zone_number_start', '')
        
        lands = list(db.lands.find())
        for land in lands:
            for sector in land.get('sectors', []):
                if sector['_id'] == sector_id:
                    if 'zones' not in sector:
                        sector['zones'] = []
                    
                    for idx, name in enumerate(names):
                        name = name.strip()
                        if name:
                            zone_data = ZoneModel(
                                zone_id=f"{zone_id_prefix}{idx+1}" if zone_id_prefix else '',
                                zone_number=f"Z{idx+1:02d}" if not zone_number_start else zone_number_start,
                                name=name,
                                description=request.form.get('description', ''),
                                location={
                                    'area': {'value': safe_float(request.form.get('area_value')), 'unit': request.form.get('area_unit', 'acres')},
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
                            
                            zone_dict = zone_data.model_dump()
                            zone_dict['_id'] = str(ObjectId())
                            zone_dict['rows'] = []
                            
                            sector['zones'].append(zone_dict)
                    
                    db.lands.update_one({'_id': land['_id']}, {'$set': {'sectors': land.get('sectors', [])}})
                    log_message('info', f'Bulk added {len([n for n in names if n.strip()])} zones', session.get('user_id'), session.get('username'))
                    flash('Zones added successfully!', 'success')
                    break
    except Exception as e:
        flash(f'Validation error: {str(e)}', 'danger')
    
    return redirect(url_for('zones.index'))
