import sys
import traceback
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort
from app.database import get_db
from app.utils.logging import log_message, log_func_call
from app.models.validation import TreeModel
from bson import ObjectId
from datetime import datetime

trees_bp = Blueprint('trees', __name__, url_prefix='/trees')
trees_bp.strict_slashes = False


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
@trees_bp.route('/')
def index():
    try:
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return render_template('trees/index.html', trees=[], rows=[], search='')
        search = request.args.get('search', '').strip()
        lands = list(db.lands.find())
        trees = []
        rows = []
        
        for land in lands:
            land['_id'] = str(land['_id'])
            for farm in land.get('farms', []):
                for sector in farm.get('sectors', []):
                    sector['_id'] = str(sector['_id'])
                    for zone in sector.get('zones', []):
                        zone['_id'] = str(zone['_id'])
                        zone['sector'] = sector
                        for row in zone.get('rows', []):
                            row['_id'] = str(row['_id'])
                            row['zone'] = zone
                            rows.append(row)
                            for tree in row.get('trees', []):
                                if search and search.lower() not in tree.get('name', '').lower():
                                    continue
                                tree['_id'] = str(tree.get('_id', ''))
                                tree['row'] = row
                                trees.append(tree)
        
        return render_template('trees/index.html', trees=trees, rows=rows, search=search)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"trees.index() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error: {err["message"]}', 'danger')
        return render_template('trees/index.html', trees=[], rows=[], search='')


@log_func_call
@trees_bp.route('/add', methods=['POST'])
def add():
    try:
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('lands.index'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('trees.index'))
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
            
            tree_dict = tree_data.model_dump()
            tree_dict['_id'] = str(ObjectId())
            tree_dict['name'] = request.form.get('name', 'Tree')
            
            lands = list(db.lands.find())
            for land in lands:
                for farm in land.get('farms', []):
                    for sector in farm.get('sectors', []):
                        for zone in sector.get('zones', []):
                            if str(zone['_id']) == zone_id:
                                db.lands.update_one(
                                    {'_id': land['_id'], 'sectors.zones._id': zone['_id'], 'sectors.zones.$.rows._id': row_id},
                                    {'$push': {'sectors.$[elem].zones.$[elem2].rows.$[elem3].trees': tree_dict}, '$set': {'last_updated_at': datetime.now().isoformat()}},
                                    array_filters=[{'elem._id': sector['_id']}, {'elem2._id': zone['_id']}, {'elem3._id': row_id}]
                                )
                                log_message('info', f"Added tree: {tree_dict['name']}", session.get('user_id'), session.get('username'))
                                flash('Tree added successfully!', 'success')
                                break
        except Exception as ve:
            flash(f'Validation error: {str(ve)}', 'danger')
        
        return redirect(url_for('trees.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"trees.add() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error adding tree: {err["message"]}', 'danger')
        return redirect(url_for('trees.index'))


@log_func_call
@trees_bp.route('/<tree_id>')
def detail(tree_id):
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
                        zone['_id'] = str(zone['_id'])
                        for row in zone.get('rows', []):
                            row['_id'] = str(row['_id'])
                            for tree in row.get('trees', []):
                                if str(tree.get('_id', '')) == tree_id:
                                    tree['_id'] = str(tree['_id'])
                                    return render_template('trees/detail.html', tree=tree, row=row, zone=zone, sector=sector, land=land, farm=farm)
        
        abort(404)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"trees.detail() line {err['line']}: {err['message']}\n{err['trace']}")
        abort(500)


@log_func_call
@trees_bp.route('/<tree_id>/edit', methods=['POST'])
def edit(tree_id):
    try:
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('lands.index'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('trees.index'))
        lands = list(db.lands.find())
        
        for land in lands:
            for farm in land.get('farms', []):
                for sector in farm.get('sectors', []):
                    for zone in sector.get('zones', []):
                        for row in zone.get('rows', []):
                            for tree in row.get('trees', []):
                                if str(tree.get('_id', '')) == tree_id:
                                    tree['name'] = request.form.get('name', tree.get('name', 'Tree'))
                                if request.form.get('tree_number'):
                                    tree['tree_number'] = request.form.get('tree_number')
                                if 'basic_info' not in tree:
                                    tree['basic_info'] = {}
                                tree['basic_info']['species'] = request.form.get('species', tree['basic_info'].get('species', ''))
                                tree['basic_info']['variety'] = request.form.get('crop_variety', tree['basic_info'].get('variety', ''))
                                tree['basic_info']['planting_date'] = request.form.get('planting_date', tree['basic_info'].get('planting_date', ''))
                                tree['basic_info']['age_years'] = int(request.form.get('age', tree['basic_info'].get('age_years', 0)) or 0)
                                if 'location_precise' not in tree:
                                    tree['location_precise'] = {}
                                tree['location_precise']['latitude'] = float(request.form.get('latitude', tree['location_precise'].get('latitude', 0)) or 0)
                                tree['location_precise']['longitude'] = float(request.form.get('longitude', tree['location_precise'].get('longitude', 0)) or 0)
                                if 'metadata' not in tree:
                                    tree['metadata'] = {}
                                tree['metadata']['status'] = request.form.get('status', tree['metadata'].get('status', 'healthy'))
                                
                                db.lands.update_one({'_id': land['_id']}, {'$set': {'farms': land.get('farms', []), 'last_updated_at': datetime.now().isoformat()}})
                                log_message('info', f'Updated tree: {tree.get("name")}', session.get('user_id'), session.get('username'))
                                flash('Tree updated successfully!', 'success')
        return redirect(url_for('trees.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"trees.edit() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error updating tree: {err["message"]}', 'danger')
        return redirect(url_for('trees.index'))


@log_func_call
@trees_bp.route('/<tree_id>/delete', methods=['POST'])
def delete(tree_id):
    try:
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('lands.index'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('trees.index'))
        lands = list(db.lands.find())
        for land in lands:
            for farm in land.get('farms', []):
                for sector in farm.get('sectors', []):
                    for zone in sector.get('zones', []):
                        for row in zone.get('rows', []):
                            trees = row.get('trees', [])
                            for i, tree in enumerate(trees):
                                if str(tree.get('_id', '')) == tree_id:
                                    tree_name = tree.get('name', 'Unknown')
                                    trees.pop(i)
                                row['trees'] = trees
                                db.lands.update_one({'_id': land['_id']}, {'$set': {'farms': land.get('farms', []), 'last_updated_at': datetime.now().isoformat()}})
                                log_message('info', f"Deleted tree: {tree_name}", session.get('user_id'), session.get('username'))
                                flash('Tree deleted successfully!', 'success')
                                return redirect(url_for('trees.index'))
        flash('Tree not found', 'danger')
        return redirect(url_for('trees.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"trees.delete() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error deleting tree: {err["message"]}', 'danger')
        return redirect(url_for('trees.index'))


@log_func_call
@trees_bp.route('/bulk_add', methods=['POST'])
def bulk_add():
    try:
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('lands.index'))
        
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('trees.index'))
        row_id = request.form.get('row_id')
        count = int(request.form.get('count', 1))
        
        lands = list(db.lands.find())
        for land in lands:
            for farm in land.get('farms', []):
                for sector in farm.get('sectors', []):
                    for zone in sector.get('zones', []):
                        for row in zone.get('rows', []):
                            if str(row.get('_id', '')) == row_id:
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
                                db.lands.update_one({'_id': land['_id']}, {'$set': {'farms': land.get('farms', []), 'last_updated_at': datetime.now().isoformat()}})
                                log_message('info', f'Bulk added {count} trees', session.get('user_id'), session.get('username'))
                                flash('Trees added successfully!', 'success')
                                break
        
        return redirect(url_for('trees.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"trees.bulk_add() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error bulk adding trees: {err["message"]}', 'danger')
        return redirect(url_for('trees.index'))
