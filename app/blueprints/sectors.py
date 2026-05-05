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
        # Validate with SectorModel
        sector_data = SectorModel(
            name=request.form.get('name', ''),
            description=request.form.get('description', ''),
            location={
                'area': {'value': float(request.form.get('area', 0) or 0), 'unit': request.form.get('area_unit', 'acres')},
                'soil_type': request.form.get('soil_type', 'loam'),
                'slope': request.form.get('slope', ''),
                'irrigation_type': request.form.get('irrigation_type', '')
            },
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

@sectors_bp.route('/<sector_id>/edit', methods=['POST'])
def edit(sector_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    lands = list(db.lands.find())
    
    for land in lands:
        for sector in land.get('sectors', []):
            if sector['_id'] == sector_id:
                try:
                    # Validate with SectorModel
                    sector_data = SectorModel(
                        name=request.form.get('name', ''),
                        description=request.form.get('description', ''),
                        location={
                            'area': {'value': float(request.form.get('area', 0) or 0), 'unit': request.form.get('area_unit', 'acres')},
                            'soil_type': request.form.get('soil_type', 'loam'),
                            'slope': request.form.get('slope', ''),
                            'irrigation_type': request.form.get('irrigation_type', '')
                        },
                        metadata={
                            'status': request.form.get('status', 'active'),
                            'notes': request.form.get('notes', '')
                        }
                    )
                    
                    # Update sector with validated data
                    sector['name'] = sector_data.name
                    sector['description'] = sector_data.description
                    sector['location'] = sector_data.location
                    sector['metadata'] = sector_data.metadata
                    
                    db.lands.update_one({'_id': land['_id']}, {'$set': {'sectors': land.get('sectors', [])}})
                    log_message('info', f"Updated sector: {sector_data.name}", session.get('user_id'), session.get('username'))
                    flash('Sector updated successfully!', 'success')
                except Exception as e:
                    flash(f'Validation error: {str(e)}', 'danger')
                return redirect(url_for('sectors.index'))
    
    abort(404)

@sectors_bp.route('/bulk_add', methods=['POST'])
def bulk_add():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    land_id = request.form.get('land_id')
    names = request.form.get('names', '').strip().split('\n')
    
    lands = list(db.lands.find())
    for land in lands:
        if str(land['_id']) == land_id:
            if 'sectors' not in land:
                land['sectors'] = []
            for name in names:
                name = name.strip()
                if name:
                    land['sectors'].append({
                        '_id': str(ObjectId()),
                        'name': name,
                        'zones': []
                    })
            db.lands.update_one({'_id': land['_id']}, {'$set': {'sectors': land.get('sectors', [])}})
            log_message('info', f'Bulk added {len([n for n in names if n.strip()])} sectors', session.get('user_id'), session.get('username'))
            flash('Sectors added successfully!', 'success')
            break
    
    return redirect(url_for('sectors.index'))
