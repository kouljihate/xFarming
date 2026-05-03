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
    name = request.form.get('name')
    sector_id = request.form.get('sector_id')
    
    try:
        zone_data = ZoneModel(name=name)
        
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
                    log_message('info', f"Added zone: {name}", session.get('user_id'), session.get('username'))
                    flash('Zone added successfully!', 'success')
                    break
    except Exception as e:
        flash(f'Validation error: {str(e)}', 'danger')
    
    return redirect(url_for('zones.index'))

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
    lands = list(db.lands.find())
    
    for land in lands:
        for sector in land.get('sectors', []):
            for zone in sector.get('zones', []):
                if zone['_id'] == zone_id:
                    new_name = request.form.get('name')
                    zone['name'] = new_name
                    db.lands.update_one({'_id': land['_id']}, {'$set': {'sectors': land.get('sectors', [])}})
                    log_message('info', f"Updated zone: {new_name}", session.get('user_id'), session.get('username'))
                    flash('Zone updated successfully!', 'success')
                    return redirect(url_for('zones.index'))
    
    abort(404)

@zones_bp.route('/bulk_add', methods=['POST'])
def bulk_add():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    sector_id = request.form.get('sector_id')
    names = request.form.get('names', '').strip().split('\n')
    
    lands = list(db.lands.find())
    for land in lands:
        for sector in land.get('sectors', []):
            if sector['_id'] == sector_id:
                if 'zones' not in sector:
                    sector['zones'] = []
                for name in names:
                    name = name.strip()
                    if name:
                        sector['zones'].append({
                            '_id': str(ObjectId()),
                            'name': name,
                            'rows': []
                        })
                db.lands.update_one({'_id': land['_id']}, {'$set': {'sectors': land.get('sectors', [])}})
                log_message('info', f'Bulk added {len([n for n in names if n.strip()])} zones', session.get('user_id'), session.get('username'))
                flash('Zones added successfully!', 'success')
                break
    
    return redirect(url_for('zones.index'))
