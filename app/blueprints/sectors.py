from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort
from app.database import get_db
from app.utils.logging import log_message
from app.models.validation import SectorModel
from bson import ObjectId

sectors_bp = Blueprint('sectors', __name__, url_prefix='/sectors')
sectors_bp.strict_slashes = False

@sectors_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    search = request.args.get('search', '').strip()
    lands = list(db.lands.find())
    sectors = []
    lands_for_select = []
    
    for land in lands:
        land['_id'] = str(land['_id'])
        lands_for_select.append(land)
        for sector in land.get('sectors', []):
            if search and search.lower() not in sector['name'].lower():
                continue
            sector['land'] = land
            sector['land_id'] = land['_id']
            sector['zone_count'] = len(sector.get('zones', []))
            sectors.append(sector)
    
    return render_template('sectors/index.html', sectors=sectors, lands=lands_for_select, search=search)

@sectors_bp.route('/add', methods=['POST'])
def add():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    land_id = request.form.get('land_id')
    
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
        
        lands = list(db.lands.find())
        for land in lands:
            if str(land['_id']) == land_id:
                if 'sectors' not in land:
                    land['sectors'] = []
                
                sector_dict = sector_data.model_dump()
                sector_dict['_id'] = str(ObjectId())
                sector_dict['zones'] = []
                
                land['sectors'].append(sector_dict)
                db.lands.update_one({'_id': land['_id']}, {'$set': {'sectors': land.get('sectors', [])}})
                log_message('info', f"Added sector: {sector_data.name}", session.get('user_id'), session.get('username'))
                flash('Sector added successfully!', 'success')
                break
    except Exception as e:
        flash(f'Validation error: {str(e)}', 'danger')
    
    return redirect(url_for('sectors.index'))

@sectors_bp.route('/<sector_id>')
def detail(sector_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    lands = list(db.lands.find())
    
    for land in lands:
        for sector in land.get('sectors', []):
            if sector['_id'] == sector_id:
                sector['land'] = land
                sector['_id'] = str(sector['_id'])
                
                for zone in sector.get('zones', []):
                    zone['_id'] = str(zone['_id'])
                    zone['row_count'] = len(zone.get('rows', []))
                    for row in zone.get('rows', []):
                        row['_id'] = str(row['_id'])
                        row['tree_count'] = len(row.get('trees', []))
                
                return render_template('sectors/detail.html', sector=sector, land=land, zones=sector.get('zones', []))
    
    abort(404)

@sectors_bp.route('/<sector_id>/edit', methods=['GET', 'POST'])
def edit(sector_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    lands = list(db.lands.find())
    
    for land in lands:
        for sector in land.get('sectors', []):
            if sector['_id'] == sector_id:
                if request.method == 'POST':
                    try:
                        import json
                        
                        # Parse boundary if provided
                        boundary = None
                        boundary_str = request.form.get('boundary', '').strip()
                        if boundary_str:
                            try:
                                boundary = json.loads(boundary_str)
                            except:
                                boundary = sector.get('boundary', {'type': 'Polygon', 'coordinates': []})
                        else:
                            boundary = sector.get('boundary', {'type': 'Polygon', 'coordinates': []})
                        
                        # Get sector_id and sector_number
                        sector_id_val = request.form.get('sector_id', '').strip()
                        sector_number = request.form.get('sector_number', sector.get('sector_number', 1))
                        try:
                            sector_number = int(sector_number)
                        except:
                            sector_number = 1
                        
                        # Validate with SectorModel
                        sector_data = SectorModel(
                            sector_id=sector_id_val,
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
                        
                        # Update sector with validated data
                        sector['sector_id'] = sector_data.sector_id
                        sector['sector_number'] = sector_data.sector_number
                        sector['name'] = sector_data.name
                        sector['description'] = sector_data.description
                        sector['location'] = sector_data.location
                        sector['boundary'] = sector_data.boundary
                        sector['metadata'] = sector_data.metadata
                        
                        db.lands.update_one({'_id': land['_id']}, {'$set': {'sectors': land.get('sectors', [])}})
                        log_message('info', f"Updated sector: {sector_data.name}", session.get('user_id'), session.get('username'))
                        flash('Sector updated successfully!', 'success')
                    except Exception as e:
                        flash(f'Validation error: {str(e)}', 'danger')
                    return redirect(url_for('sectors.index'))
                else:
                    # GET request - render edit form
                    return render_template('sectors/edit.html', sector=sector, land=land)
    
    abort(404)

@sectors_bp.route('/bulk_add', methods=['POST'])
def bulk_add():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    land_id = request.form.get('land_id')
    
    # Get bulk parameters
    start_with = request.form.get('start_with', 'Sector').strip()
    start_number = request.form.get('start_number', 1)
    count = request.form.get('count', 5)
    
    try:
        start_number = int(start_number)
        count = int(count)
    except:
        start_number = 1
        count = 5
    
    # Generate names
    names = [f"{start_with} {i}" for i in range(start_number, start_number + count)]
    
    # Get other fields
    description = request.form.get('description', '')
    area_value = request.form.get('area', 0)
    area_unit = request.form.get('area_unit', 'acres')
    soil_type = request.form.get('soil_type', 'loam')
    slope = request.form.get('slope', '')
    irrigation_type = request.form.get('irrigation_type', '')
    
    lands = list(db.lands.find())
    for land in lands:
        if str(land['_id']) == land_id:
            if 'sectors' not in land:
                land['sectors'] = []
            added_count = 0
            for idx, name in enumerate(names):
                try:
                    # Validate with SectorModel
                    sector_data = SectorModel(
                        sector_number=start_number + idx,
                        name=name,
                        description=description,
                        location={
                            'area': {'value': float(area_value) or 0, 'unit': area_unit},
                            'soil_type': soil_type,
                            'slope': slope,
                            'irrigation_type': irrigation_type
                        },
                        metadata={
                            'status': 'active',
                            'notes': ''
                        }
                    )
                    sector_dict = sector_data.model_dump()
                    sector_dict['_id'] = str(ObjectId())
                    sector_dict['zones'] = []
                    land['sectors'].append(sector_dict)
                    added_count += 1
                except Exception as e:
                    flash(f'Validation error for "{name}": {str(e)}', 'danger')
            if added_count > 0:
                db.lands.update_one({'_id': land['_id']}, {'$set': {'sectors': land.get('sectors', [])}})
                log_message('info', f'Bulk added {added_count} sectors', session.get('user_id'), session.get('username'))
                flash(f'{added_count} sectors added successfully!', 'success')
            break
    
    return redirect(url_for('sectors.index'))
