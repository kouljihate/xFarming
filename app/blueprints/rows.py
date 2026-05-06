from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort
from app.database import get_db
from app.utils.logging import log_message
from app.models.validation import RowModel
from bson import ObjectId

rows_bp = Blueprint('rows', __name__, url_prefix='/rows')
rows_bp.strict_slashes = False

@rows_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    search = request.args.get('search', '').strip()
    lands = list(db.lands.find())
    rows = []
    zones = []
    
    for land in lands:
        land['_id'] = str(land['_id'])
        for sector in land.get('sectors', []):
            sector['_id'] = str(sector['_id'])
            for zone in sector.get('zones', []):
                zone['_id'] = str(zone['_id'])
                zone['sector'] = sector
                zones.append(zone)
                for row in zone.get('rows', []):
                    if search and search.lower() not in row['name'].lower():
                        continue
                    row['_id'] = str(row['_id'])
                    row['zone'] = zone
                    row['zone_id'] = zone['_id']
                    row['tree_count'] = len(row.get('trees', []))
                    rows.append(row)
    
    return render_template('rows/index.html', rows=rows, zones=zones, search=search)

@rows_bp.route('/add', methods=['POST'])
def add():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    zone_id = request.form.get('zone_id')
    
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
        
        # Validate with RowModel
        row_data = RowModel(
            row_number=safe_int(request.form.get('row_number'), 1),
            name=request.form.get('name', ''),
            description=request.form.get('description', ''),
            position={
                'start_coordinates': {
                    'latitude': safe_float(request.form.get('start_latitude')),
                    'longitude': safe_float(request.form.get('start_longitude'))
                },
                'end_coordinates': {
                    'latitude': safe_float(request.form.get('end_latitude')),
                    'longitude': safe_float(request.form.get('end_longitude'))
                },
                'length': {'value': safe_float(request.form.get('length_value')), 'unit': request.form.get('length_unit', 'feet')},
                'orientation': request.form.get('orientation', '')
            },
            tree_count={
                'total_positions': safe_int(request.form.get('total_positions')),
                'active_trees': safe_int(request.form.get('active_trees')),
                'empty_positions': safe_int(request.form.get('empty_positions')),
                'dead_trees': safe_int(request.form.get('dead_trees')),
                'replacement_needed': 0
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
                'notes': request.form.get('notes', '')
            }
        )
        
        # Use $push with array filters to add row to the correct zone
        row_dict = row_data.model_dump()
        row_dict['_id'] = str(ObjectId())
        row_dict['trees'] = []
        
        lands = list(db.lands.find())
        for land in lands:
            if str(land['_id']) == land_id:
                db.lands.update_one(
                    {'_id': land['_id'], 'sectors.zones._id': zone_id},
                    {'$push': {'sectors.$[elem].zones.$[elem2].rows': row_dict}},
                    array_filters=[{'elem.zones._id': zone_id}, {'elem2._id': zone_id}]
                )
                log_message('info', f"Added row: {row_data.name}", session.get('user_id'), session.get('username'))
                flash('Row added successfully!', 'success')
                break
    except Exception as e:
        flash(f'Validation error: {str(e)}', 'danger')
    
    return redirect(url_for('rows.index'))

@rows_bp.route('/<row_id>')
def detail(row_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    lands = list(db.lands.find())
    
    for land in lands:
        land['_id'] = str(land['_id'])
        for sector in land.get('sectors', []):
            sector['_id'] = str(sector['_id'])
            for zone in sector.get('zones', []):
                zone['_id'] = str(zone['_id'])
                for row in zone.get('rows', []):
                    if row['_id'] == row_id:
                        row['_id'] = str(row['_id'])
                        trees = row.get('trees', [])
                        for tree in trees:
                            tree['_id'] = str(tree['_id'])
                        return render_template('rows/detail.html', row=row, zone=zone, sector=sector, land=land, trees=trees)
    
    abort(404)

@rows_bp.route('/<row_id>/edit', methods=['POST'])
def edit(row_id):
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
        
        # Validate with RowModel
        row_data = RowModel(
            row_number=safe_int(request.form.get('row_number'), 1),
            name=request.form.get('name', ''),
            description=request.form.get('description', ''),
            position={
                'start_coordinates': {
                    'latitude': safe_float(request.form.get('start_latitude')),
                    'longitude': safe_float(request.form.get('start_longitude'))
                },
                'end_coordinates': {
                    'latitude': safe_float(request.form.get('end_latitude')),
                    'longitude': safe_float(request.form.get('end_longitude'))
                },
                'length': {'value': safe_float(request.form.get('length_value')), 'unit': request.form.get('length_unit', 'feet')},
                'orientation': request.form.get('orientation', '')
            },
            tree_count={
                'total_positions': safe_int(request.form.get('total_positions')),
                'active_trees': safe_int(request.form.get('active_trees')),
                'empty_positions': safe_int(request.form.get('empty_positions')),
                'dead_trees': safe_int(request.form.get('dead_trees')),
                'replacement_needed': 0
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
                'notes': request.form.get('notes', '')
            }
        )
        
        lands = list(db.lands.find())
        for land in lands:
            for sector in land.get('sectors', []):
                for zone in sector.get('zones', []):
                    rows = zone.get('rows', [])
                    for row in rows:
                        if row['_id'] == row_id:
                            # Update row with validated data
                            row['row_number'] = row_data.row_number
                            row['name'] = row_data.name
                            row['description'] = row_data.description
                            row['position'] = row_data.position
                            row['tree_count'] = row_data.tree_count
                            row['maintenance'] = row_data.maintenance
                            row['metadata'] = row_data.metadata
                            
                            db.lands.update_one({'_id': land['_id']}, {'$set': {'sectors': land.get('sectors', [])}})
                            log_message('info', f"Updated row: {row_data.name}", session.get('user_id'), session.get('username'))
                            flash('Row updated successfully!', 'success')
                            return redirect(url_for('rows.index'))
    except Exception as e:
        flash(f'Validation error: {str(e)}', 'danger')
    
    return redirect(url_for('rows.index'))

@rows_bp.route('/bulk_add', methods=['POST'])
def bulk_add():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    zone_id = request.form.get('zone_id')
    
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
        
        # Get row_number start and name prefix
        row_number_start = request.form.get('row_number_start', '')
        name_prefix = request.form.get('name_prefix', '').strip()
        
        lands = list(db.lands.find())
        for land in lands:
            for sector in land.get('sectors', []):
                for zone in sector.get('zones', []):
                    if zone['_id'] == zone_id:
                        if 'rows' not in zone:
                            zone['rows'] = []
                        
                        for idx, name in enumerate(names):
                            name = name.strip()
                            if name:
                                row_data = RowModel(
                                    row_number=safe_int(request.form.get('row_number_start')) if row_number_start else idx+1,
                                    name=name_prefix + name if name_prefix else name,
                                    description=request.form.get('description', ''),
                                    position={
                                        'start_coordinates': {
                                            'latitude': safe_float(request.form.get('start_latitude')),
                                            'longitude': safe_float(request.form.get('start_longitude'))
                                        },
                                        'end_coordinates': {
                                            'latitude': safe_float(request.form.get('end_latitude')),
                                            'longitude': safe_float(request.form.get('end_longitude'))
                                        },
                                        'length': {'value': safe_float(request.form.get('length_value')), 'unit': request.form.get('length_unit', 'feet')},
                                        'orientation': request.form.get('orientation', '')
                                    },
                                    tree_count={
                                        'total_positions': safe_int(request.form.get('total_positions')),
                                        'active_trees': safe_int(request.form.get('active_trees')),
                                        'empty_positions': safe_int(request.form.get('empty_positions')),
                                        'dead_trees': safe_int(request.form.get('dead_trees')),
                                        'replacement_needed': 0
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
                                        'notes': request.form.get('notes', '')
                                    }
                                )
                                
                                row_dict = row_data.model_dump()
                                row_dict['_id'] = str(ObjectId())
                                row_dict['trees'] = []
                                
                                zone['rows'].append(row_dict)
                        
                        db.lands.update_one({'_id': land['_id']}, {'$set': {'sectors': land.get('sectors', [])}})
                        log_message('info', f'Bulk added {len([n for n in names if n.strip()])} rows', session.get('user_id'), session.get('username'))
                        flash('Rows added successfully!', 'success')
                        break
    except Exception as e:
        flash(f'Validation error: {str(e)}', 'danger')
    
    return redirect(url_for('rows.index'))
