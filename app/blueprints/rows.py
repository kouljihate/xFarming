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
    name = request.form.get('name')
    zone_id = request.form.get('zone_id')
    
    try:
        row_data = RowModel(name=name)
        
        lands = list(db.lands.find())
        for land in lands:
            for sector in land.get('sectors', []):
                for zone in sector.get('zones', []):
                    if zone['_id'] == zone_id:
                        if 'rows' not in zone:
                            zone['rows'] = []
                        
                        row_dict = row_data.model_dump()
                        row_dict['_id'] = str(ObjectId())
                        row_dict['row_number'] = len(zone['rows'])+1
                        row_dict['trees'] = []
                        
                        zone['rows'].append(row_dict)
                        db.lands.update_one({'_id': land['_id']}, {'$set': {'sectors': land.get('sectors', [])}})
                        log_message('info', f"Added row: {name}", session.get('user_id'), session.get('username'))
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

@rows_bp.route('/bulk_add', methods=['POST'])
def bulk_add():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    zone_id = request.form.get('zone_id')
    names = request.form.get('names', '').strip().split('\n')
    
    lands = list(db.lands.find())
    for land in lands:
        for sector in land.get('sectors', []):
            for zone in sector.get('zones', []):
                if zone['_id'] == zone_id:
                    if 'rows' not in zone:
                        zone['rows'] = []
                    for name in names:
                        name = name.strip()
                        if name:
                            zone['rows'].append({
                                '_id': str(ObjectId()),
                                'row_number': len(zone['rows'])+1,
                                'name': name,
                                'trees': []
                            })
                    db.lands.update_one({'_id': land['_id']}, {'$set': {'sectors': land.get('sectors', [])}})
                    log_message('info', f'Bulk added {len([n for n in names if n.strip()])} rows', session.get('user_id'), session.get('username'))
                    flash('Rows added successfully!', 'success')
                    break
    
    return redirect(url_for('rows.index'))
