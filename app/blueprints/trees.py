from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort
from app.database import get_db
from app.utils.logging import log_message
from app.models.validation import TreeModel
from bson import ObjectId

trees_bp = Blueprint('trees', __name__, url_prefix='/trees')
trees_bp.strict_slashes = False

@trees_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    search = request.args.get('search', '').strip()
    lands = list(db.lands.find())
    trees = []
    rows = []
    
    for land in lands:
        land['_id'] = str(land['_id'])
        for sector in land.get('sectors', []):
            sector['_id'] = str(sector['_id'])
            for zone in sector.get('zones', []):
                zone['_id'] = str(zone['_id'])
                zone['sector'] = sector
                for row in zone.get('rows', []):
                    row['_id'] = str(row['_id'])
                    row['zone'] = zone
                    rows.append(row)
                    for tree in row.get('trees', []):
                        if search and search.lower() not in tree['name'].lower():
                            continue
                        tree['_id'] = str(tree['_id'])
                        tree['row'] = row
                        trees.append(tree)
    
    return render_template('trees/index.html', trees=trees, rows=rows, search=search)

@trees_bp.route('/add', methods=['POST'])
def add():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    row_id = request.form.get('row_id')
    
    try:
        tree_data = TreeModel(
            tree_id=f"T{request.form.get('tree_number', '001')}",
            basic_info={
                'species': request.form.get('species', ''),
                'variety': request.form.get('crop_variety', ''),
                'planting_date': request.form.get('planting_date', ''),
                'age_years': int(request.form.get('age', 0) or 0)
            },
            location_precise={
                'latitude': float(request.form.get('latitude', 0) or 0),
                'longitude': float(request.form.get('longitude', 0) or 0)
            },
            metadata={'status': request.form.get('status', 'healthy')}
        )
        
        # Use $push with array filters to add tree to the correct row
        tree_dict = tree_data.model_dump()
        tree_dict['_id'] = str(ObjectId())
        tree_dict['name'] = request.form.get('name', 'Tree')  # For display purposes
        
        lands = list(db.lands.find())
        for land in lands:
            for sector in land.get('sectors', []):
                for zone in sector.get('zones', []):
                    if str(zone['_id']) == zone_id:
                        db.lands.update_one(
                            {'_id': land['_id'], 'sectors.zones._id': zone['_id'], 'sectors.zones.$.rows._id': row_id},
                            {'$push': {'sectors.$[elem].zones.$[elem2].rows.$[elem3].trees': tree_dict}},
                            array_filters=[{'elem._id': sector['_id']}, {'elem2._id': zone['_id']}, {'elem3._id': row_id}]
                        )
                        log_message('info', f"Added tree: {tree_dict['name']}", session.get('user_id'), session.get('username'))
                        flash('Tree added successfully!', 'success')
                        break
    except Exception as e:
        flash(f'Validation error: {str(e)}', 'danger')
    
    return redirect(url_for('trees.index'))

@trees_bp.route('/<tree_id>')
def detail(tree_id):
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
                    row['_id'] = str(row['_id'])
                    for tree in row.get('trees', []):
                        if tree['_id'] == tree_id:
                            tree['_id'] = str(tree['_id'])
                            return render_template('trees/detail.html', tree=tree, row=row, zone=zone, sector=sector, land=land)
    
    abort(404)

@trees_bp.route('/<tree_id>/edit', methods=['POST'])
def edit(tree_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    lands = list(db.lands.find())
    
    for land in lands:
        for sector in land.get('sectors', []):
            for zone in sector.get('zones', []):
                for row in zone.get('rows', []):
                    for tree in row.get('trees', []):
                        if tree['_id'] == tree_id:
                            # Update display name
                            tree['name'] = request.form.get('name', tree.get('name', 'Tree'))
                            # Update tree_number
                            if request.form.get('tree_number'):
                                tree['tree_number'] = request.form.get('tree_number')
                            # Update basic_info
                            if 'basic_info' not in tree:
                                tree['basic_info'] = {}
                            tree['basic_info']['species'] = request.form.get('species', tree['basic_info'].get('species', ''))
                            tree['basic_info']['variety'] = request.form.get('crop_variety', tree['basic_info'].get('variety', ''))
                            tree['basic_info']['planting_date'] = request.form.get('planting_date', tree['basic_info'].get('planting_date', ''))
                            tree['basic_info']['age_years'] = int(request.form.get('age', tree['basic_info'].get('age_years', 0)) or 0)
                            # Update location_precise
                            if 'location_precise' not in tree:
                                tree['location_precise'] = {}
                            tree['location_precise']['latitude'] = float(request.form.get('latitude', tree['location_precise'].get('latitude', 0)) or 0)
                            tree['location_precise']['longitude'] = float(request.form.get('longitude', tree['location_precise'].get('longitude', 0)) or 0)
                            # Update metadata (status)
                            if 'metadata' not in tree:
                                tree['metadata'] = {}
                            tree['metadata']['status'] = request.form.get('status', tree['metadata'].get('status', 'healthy'))
                            
                            db.lands.update_one({'_id': land['_id']}, {'$set': {'sectors': land.get('sectors', [])}})
                            log_message('info', f'Updated tree: {tree.get("name")}', session.get('user_id'), session.get('username'))
                            flash('Tree updated successfully!', 'success')
    return redirect(url_for('trees.index'))

@trees_bp.route('/<tree_id>/delete', methods=['POST'])
def delete(tree_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    lands = list(db.lands.find())
    for land in lands:
        for sector in land.get('sectors', []):
            for zone in sector.get('zones', []):
                for row in zone.get('rows', []):
                    trees = row.get('trees', [])
                    for i, tree in enumerate(trees):
                        if tree['_id'] == tree_id:
                            tree_name = tree.get('name', 'Unknown')
                            trees.pop(i)
                            row['trees'] = trees
                            db.lands.update_one({'_id': land['_id']}, {'$set': {'sectors': land.get('sectors', [])}})
                            log_message('info', f"Deleted tree: {tree_name}", session.get('user_id'), session.get('username'))
                            flash('Tree deleted successfully!', 'success')
                            return redirect(url_for('trees.index'))
    flash('Tree not found', 'danger')
    return redirect(url_for('trees.index'))
    
    abort(404)

@trees_bp.route('/bulk_add', methods=['POST'])
def bulk_add():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.index'))
    
    db = get_db()
    row_id = request.form.get('row_id')
    count = int(request.form.get('count', 1))
    
    lands = list(db.lands.find())
    for land in lands:
        for sector in land.get('sectors', []):
            for zone in sector.get('zones', []):
                for row in zone.get('rows', []):
                    if row['_id'] == row_id:
                        if 'trees' not in row:
                            row['trees'] = []
                        for i in range(count):
                            row['trees'].append({
                                '_id': str(ObjectId()),
                                'tree_id': f"T{len(row['trees'])+1:03d}",
                                'name': f'Tree {len(row["trees"])+1}',
                                'planting_date': '',
                                'crop_variety': '',
                                'age': 0,
                                'status': 'healthy',
                                'height': 0.0,
                                'health_status': 'good',
                                'last_inspection': '',
                                'latitude': 0.0,
                                'longitude': 0.0
                            })
                        db.lands.update_one({'_id': land['_id']}, {'$set': {'sectors': land.get('sectors', [])}})
                        log_message('info', f'Bulk added {count} trees', session.get('user_id'), session.get('username'))
                        flash('Trees added successfully!', 'success')
                        break
    
    return redirect(url_for('trees.index'))
