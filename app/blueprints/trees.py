import sys
import traceback
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort
from app.database import get_db, find_doc
from app.utils.logging import log_message, log_func_call, login_required, admin_required
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
        farms = list(db.farms.find())
        trees = []
        rows = []

        for farm in farms:
            farm['_id'] = str(farm['_id'])
            for sector in farm.get('sectors', []):
                sector['_id'] = str(sector['_id'])
                for zone in sector.get('zones', []):
                    zone['_id'] = str(zone['_id'])
                    for row in zone.get('rows', []):
                        row['_id'] = str(row.get('_id', ''))
                        row['zone'] = zone
                        row['farm'] = farm
                        rows.append(row)
                        for tree in row.get('trees', []):
                            if search and search.lower() not in tree.get('name', '').lower():
                                continue
                            tree['_id'] = str(tree.get('_id', ''))
                            tree['row'] = row
                            tree['farm'] = farm
                            trees.append(tree)

        return render_template('trees/index.html', trees=trees, rows=rows, search=search)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"trees.index() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error: {err["message"]}', 'danger')
        return render_template('trees/index.html', trees=[], rows=[], search='')


@log_func_call
@admin_required
@trees_bp.route('/add', methods=['POST'])
def add():
    try:
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('trees.index'))

        farm_id = request.form.get('farm_id', '')
        row_id = request.form.get('row_id', '')

        farm = find_doc(db.farms, farm_id) if farm_id else None
        if not farm:
            flash('Farm not found', 'danger')
            return redirect(url_for('trees.index'))

        try:
            tree_data = TreeModel(
                tree_id=f"T{request.form.get('tree_number', '001')}",
                basic_info={
                    'species': request.form.get('species', ''),
                    'variety': request.form.get('variety', ''),
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

            found = False
            for sector in farm.get('sectors', []):
                for zone in sector.get('zones', []):
                    for row in zone.get('rows', []):
                        if str(row.get('_id', '')) == row_id:
                            if 'trees' not in row:
                                row['trees'] = []
                            row['trees'].append(tree_dict)
                            found = True
                            break
                    if found:
                        break
                if found:
                    break

            if found:
                db.farms.update_one(
                    {'_id': farm['_id']},
                    {'$set': {'sectors': farm.get('sectors', []), 'last_updated_at': datetime.utcnow()}}
                )
                log_message('info', f"Added tree: {tree_dict.get('name', '')}", session.get('user_id'), session.get('username'))
                flash('Tree added successfully!', 'success')
            else:
                flash('Row not found', 'danger')
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

        farms = list(db.farms.find())
        for farm in farms:
            farm['_id'] = str(farm['_id'])
            for sector in farm.get('sectors', []):
                sector['_id'] = str(sector['_id'])
                for zone in sector.get('zones', []):
                    zone['_id'] = str(zone['_id'])
                    for row in zone.get('rows', []):
                        row['_id'] = str(row.get('_id', ''))
                        for tree in row.get('trees', []):
                            if str(tree.get('_id', '')) == tree_id:
                                tree['_id'] = str(tree['_id'])
                                return render_template('trees/detail.html', tree=tree, row=row, zone=zone, sector=sector, farm=farm)

        abort(404)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"trees.detail() line {err['line']}: {err['message']}\n{err['trace']}")
        abort(500)


@log_func_call
@admin_required
@trees_bp.route('/<tree_id>/edit', methods=['POST'])
def edit(tree_id):
    try:
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('trees.index'))

        farms = list(db.farms.find())
        for farm in farms:
            for sector in farm.get('sectors', []):
                for zone in sector.get('zones', []):
                    for row in zone.get('rows', []):
                        for tree in row.get('trees', []):
                            if str(tree.get('_id', '')) == tree_id:
                                try:
                                    tree['name'] = request.form.get('name', tree.get('name', 'Tree'))
                                    if request.form.get('tree_number'):
                                        tree['tree_number'] = request.form.get('tree_number')
                                    if 'basic_info' not in tree:
                                        tree['basic_info'] = {}
                                    tree['basic_info']['species'] = request.form.get('species', tree['basic_info'].get('species', ''))
                                    tree['basic_info']['variety'] = request.form.get('variety', tree['basic_info'].get('variety', ''))
                                    tree['basic_info']['planting_date'] = request.form.get('planting_date', tree['basic_info'].get('planting_date', ''))
                                    tree['basic_info']['age_years'] = int(request.form.get('age', tree['basic_info'].get('age_years', 0)) or 0)
                                    if 'location_precise' not in tree:
                                        tree['location_precise'] = {}
                                    tree['location_precise']['latitude'] = float(request.form.get('latitude', tree['location_precise'].get('latitude', 0)) or 0)
                                    tree['location_precise']['longitude'] = float(request.form.get('longitude', tree['location_precise'].get('longitude', 0)) or 0)
                                    if 'metadata' not in tree:
                                        tree['metadata'] = {}
                                    tree['metadata']['status'] = request.form.get('status', tree['metadata'].get('status', 'healthy'))

                                    db.farms.update_one({'_id': farm['_id']}, {'$set': {'sectors': farm.get('sectors', []), 'last_updated_at': datetime.utcnow()}})
                                    log_message('info', f'Updated tree: {tree.get("name")}', session.get('user_id'), session.get('username'))
                                    flash('Tree updated successfully!', 'success')
                                except Exception as ve:
                                    flash(f'Validation error: {str(ve)}', 'danger')
                                return redirect(url_for('trees.index'))

        flash('Tree not found', 'danger')
        return redirect(url_for('trees.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"trees.edit() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error updating tree: {err["message"]}', 'danger')
        return redirect(url_for('trees.index'))


@log_func_call
@admin_required
@trees_bp.route('/<tree_id>/delete', methods=['POST'])
def delete(tree_id):
    try:
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('trees.index'))

        farms = list(db.farms.find())
        for farm in farms:
            for sector in farm.get('sectors', []):
                for zone in sector.get('zones', []):
                    for row in zone.get('rows', []):
                        trees = row.get('trees', [])
                        for i, tree in enumerate(trees):
                            if str(tree.get('_id', '')) == tree_id:
                                tree_name = tree.get('name', 'Unknown')
                                trees.pop(i)
                                row['trees'] = trees
                                db.farms.update_one({'_id': farm['_id']}, {'$set': {'sectors': farm.get('sectors', []), 'last_updated_at': datetime.utcnow()}})
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
@admin_required
@trees_bp.route('/bulk_add', methods=['POST'])
def bulk_add():
    try:
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('trees.index'))

        farm_id = request.form.get('farm_id', '')
        row_id = request.form.get('row_id', '')
        count = int(request.form.get('count', 1))

        farm = find_doc(db.farms, farm_id) if farm_id else None
        if not farm:
            flash('Farm not found', 'danger')
            return redirect(url_for('trees.index'))

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
                                'variety': '',
                                'age': 0,
                                'status': 'healthy',
                                'latitude': 0.0,
                                'longitude': 0.0
                            })
                        db.farms.update_one({'_id': farm['_id']}, {'$set': {'sectors': farm.get('sectors', []), 'last_updated_at': datetime.utcnow()}})
                        log_message('info', f'Bulk added {count} trees', session.get('user_id'), session.get('username'))
                        flash('Trees added successfully!', 'success')
                        return redirect(url_for('trees.index'))

        flash('Row not found', 'danger')
        return redirect(url_for('trees.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"trees.bulk_add() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error bulk adding trees: {err["message"]}', 'danger')
        return redirect(url_for('trees.index'))
