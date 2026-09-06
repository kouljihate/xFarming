import sys
import traceback
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort
from app.database import get_db, find_doc
from app.utils.logging import log_message, log_func_call, login_required, admin_required
from app.models.validation import RowModel
from bson import ObjectId
from datetime import datetime

rows_bp = Blueprint('rows', __name__, url_prefix='/rows')
rows_bp.strict_slashes = False


def _error_info(e):
    tb = sys.exc_info()[-1]
    return {
        'error': True,
        'message': str(e),
        'function': sys._getframe(1).f_code.co_name,
        'line': tb.tb_lineno if tb else 0,
        'trace': traceback.format_exc()
    }


def _safe_float(value, default=0.0):
    try:
        return float(value or default)
    except (ValueError, TypeError):
        return default


def _safe_int(value, default=0):
    try:
        return int(value or default)
    except (ValueError, TypeError):
        return default


@log_func_call
@rows_bp.route('/')
def index():
    try:
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))

        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return render_template('rows/index.html', rows=[], zones=[], search='')

        search = request.args.get('search', '').strip()
        farms = list(db.farms.find())
        rows = []
        zones = []

        for farm in farms:
            farm['_id'] = str(farm['_id'])
            for sector in farm.get('sectors', []):
                sector['_id'] = str(sector['_id'])
                sector['farm'] = farm
                for zone in sector.get('zones', []):
                    zone['_id'] = str(zone['_id'])
                    zone['sector'] = sector
                    zone['farm'] = farm
                    zones.append(zone)
                    for row in zone.get('rows', []):
                        if search and search.lower() not in row.get('name', '').lower():
                            continue
                        row['_id'] = str(row.get('_id', ''))
                        row['zone'] = zone
                        row['zone_id'] = zone['_id']
                        row['farm_id'] = farm['_id']
                        row['tree_count'] = len(row.get('trees', []))
                        rows.append(row)

        return render_template('rows/index.html', rows=rows, zones=zones, search=search)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"rows.index() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error: {err["message"]}', 'danger')
        return render_template('rows/index.html', rows=[], zones=[], search='')


@log_func_call
@admin_required
@rows_bp.route('/add', methods=['POST'])
def add():
    try:
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('rows.index'))

        farm_id = request.form.get('farm_id', '')
        zone_id = request.form.get('zone_id', '')

        farm = find_doc(db.farms, farm_id) if farm_id else None
        if not farm:
            flash('Farm not found', 'danger')
            return redirect(url_for('rows.index'))

        try:
            row_data = RowModel(
                row_number=_safe_int(request.form.get('row_number'), 1),
                name=request.form.get('name', ''),
                description=request.form.get('description', ''),
                position={
                    'start_coordinates': {
                        'latitude': _safe_float(request.form.get('start_latitude')),
                        'longitude': _safe_float(request.form.get('start_longitude'))
                    },
                    'end_coordinates': {
                        'latitude': _safe_float(request.form.get('end_latitude')),
                        'longitude': _safe_float(request.form.get('end_longitude'))
                    },
                    'length': {'value': _safe_float(request.form.get('length_value')), 'unit': request.form.get('length_unit', 'feet')},
                    'orientation': request.form.get('orientation', '')
                },
                tree_count={
                    'total_positions': _safe_int(request.form.get('total_positions')),
                    'active_trees': _safe_int(request.form.get('active_trees')),
                    'empty_positions': _safe_int(request.form.get('empty_positions')),
                    'dead_trees': _safe_int(request.form.get('dead_trees')),
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

            for sector in farm.get('sectors', []):
                for zone in sector.get('zones', []):
                    if str(zone.get('_id', '')) == zone_id:
                        if 'rows' not in zone:
                            zone['rows'] = []
                        zone['rows'].append(row_dict)
                        db.farms.update_one(
                            {'_id': farm['_id']},
                            {'$set': {'sectors': farm.get('sectors', []), 'last_updated_at': datetime.utcnow()}}
                        )
                        log_message('info', f"Added row: {row_data.name}", session.get('user_id'), session.get('username'))
                        flash('Row added successfully!', 'success')
                        return redirect(url_for('rows.index'))
        except Exception as ve:
            flash(f'Validation error: {str(ve)}', 'danger')

        return redirect(url_for('rows.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"rows.add() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error adding row: {err["message"]}', 'danger')
        return redirect(url_for('rows.index'))


@log_func_call
@rows_bp.route('/<row_id>')
def detail(row_id):
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
                sector['farm'] = farm
                for zone in sector.get('zones', []):
                    zone['_id'] = str(zone['_id'])
                    for row in zone.get('rows', []):
                        if str(row.get('_id', '')) == row_id:
                            row['_id'] = str(row['_id'])
                            trees = row.get('trees', [])
                            for tree in trees:
                                tree['_id'] = str(tree.get('_id', ''))
                            return render_template('rows/detail.html', row=row, zone=zone, sector=sector, farm=farm, trees=trees)

        abort(404)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"rows.detail() line {err['line']}: {err['message']}\n{err['trace']}")
        abort(500)


@log_func_call
@admin_required
@rows_bp.route('/<row_id>/edit', methods=['POST'])
def edit(row_id):
    try:
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('rows.index'))

        farms = list(db.farms.find())
        for farm in farms:
            for sector in farm.get('sectors', []):
                for zone in sector.get('zones', []):
                    for row in zone.get('rows', []):
                        if str(row.get('_id', '')) == row_id:
                            try:
                                row_data = RowModel(
                                    row_number=_safe_int(request.form.get('row_number'), 1),
                                    name=request.form.get('name', ''),
                                    description=request.form.get('description', ''),
                                    position={
                                        'start_coordinates': {
                                            'latitude': _safe_float(request.form.get('start_latitude')),
                                            'longitude': _safe_float(request.form.get('start_longitude'))
                                        },
                                        'end_coordinates': {
                                            'latitude': _safe_float(request.form.get('end_latitude')),
                                            'longitude': _safe_float(request.form.get('end_longitude'))
                                        },
                                        'length': {'value': _safe_float(request.form.get('length_value')), 'unit': request.form.get('length_unit', 'feet')},
                                        'orientation': request.form.get('orientation', '')
                                    },
                                    tree_count={
                                        'total_positions': _safe_int(request.form.get('total_positions')),
                                        'active_trees': _safe_int(request.form.get('active_trees')),
                                        'empty_positions': _safe_int(request.form.get('empty_positions')),
                                        'dead_trees': _safe_int(request.form.get('dead_trees')),
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
                                        'last_updated': datetime.utcnow().isoformat(),
                                        'status': request.form.get('status', row.get('metadata', {}).get('status', 'active')),
                                        'notes': request.form.get('notes', row.get('metadata', {}).get('notes', ''))
                                    }
                                )

                                row['row_number'] = row_data.row_number
                                row['name'] = row_data.name
                                row['description'] = row_data.description
                                row['position'] = row_data.position
                                row['tree_count'] = row_data.tree_count
                                row['maintenance'] = row_data.maintenance
                                row['metadata'] = row_data.metadata

                                db.farms.update_one({'_id': farm['_id']}, {'$set': {'sectors': farm.get('sectors', []), 'last_updated_at': datetime.utcnow()}})
                                log_message('info', f"Updated row: {row_data.name}", session.get('user_id'), session.get('username'))
                                flash('Row updated successfully!', 'success')
                            except Exception as ve:
                                flash(f'Validation error: {str(ve)}', 'danger')
                            return redirect(url_for('rows.index'))

        flash('Row not found', 'danger')
        return redirect(url_for('rows.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"rows.edit() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error updating row: {err["message"]}', 'danger')
        return redirect(url_for('rows.index'))


@log_func_call
@admin_required
@rows_bp.route('/bulk_add', methods=['POST'])
def bulk_add():
    try:
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('rows.index'))

        farm_id = request.form.get('farm_id', '')
        zone_id = request.form.get('zone_id', '')

        farm = find_doc(db.farms, farm_id) if farm_id else None
        if not farm:
            flash('Farm not found', 'danger')
            return redirect(url_for('rows.index'))

        prefix = request.form.get('prefix', 'Row').strip()
        start_from = int(request.form.get('start_from', 1) or 1)
        end_at = int(request.form.get('end_at', 5) or 5)
        names = [f"{prefix} {i}" for i in range(start_from, end_at + 1)]

        added_count = 0
        for idx, name in enumerate(names):
            try:
                row_data = RowModel(
                    row_number=idx + 1,
                    name=name,
                    position={
                        'start_coordinates': {'latitude': 0.0, 'longitude': 0.0},
                        'end_coordinates': {'latitude': 0.0, 'longitude': 0.0},
                        'length': {'value': 0, 'unit': 'feet'},
                        'orientation': ''
                    },
                    tree_count={'total_positions': 0, 'active_trees': 0, 'empty_positions': 0, 'dead_trees': 0, 'replacement_needed': 0},
                    maintenance={'last_pruned': '', 'last_fertilized': '', 'last_irrigated': '', 'next_maintenance': '', 'maintenance_notes': ''},
                    metadata={'created_date': '', 'last_updated': '', 'status': 'active', 'notes': ''}
                )
                row_dict = row_data.model_dump()
                row_dict['_id'] = ObjectId()
                row_dict['trees'] = []

                for sector in farm.get('sectors', []):
                    for zone in sector.get('zones', []):
                        if str(zone.get('_id', '')) == zone_id:
                            if 'rows' not in zone:
                                zone['rows'] = []
                            zone['rows'].append(row_dict)
                            added_count += 1
                            break
            except Exception as ve:
                flash(f'Validation error for "{name}": {str(ve)}', 'danger')

        if added_count > 0:
            db.farms.update_one({'_id': farm['_id']}, {'$set': {'sectors': farm.get('sectors', []), 'last_updated_at': datetime.utcnow()}})
            log_message('info', f'Bulk added {added_count} rows', session.get('user_id'), session.get('username'))
            flash(f'{added_count} rows added successfully!', 'success')

        return redirect(url_for('rows.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"rows.bulk_add() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error bulk adding rows: {err["message"]}', 'danger')
        return redirect(url_for('rows.index'))
