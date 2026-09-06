import sys
import traceback
import json
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort
from app.database import get_db, find_doc
from app.utils.logging import log_message, log_func_call, login_required, admin_required
from app.utils.calculation import calculate_polygon_metrics, parse_simple_coordinates
from app.models.validation import SectorModel
from bson import ObjectId
from datetime import datetime

sectors_bp = Blueprint('sectors', __name__, url_prefix='/sectors')
sectors_bp.strict_slashes = False


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
@sectors_bp.route('/')
def index():
    try:
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))

        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return render_template('sectors/index.html', sectors=[], farms=[], search='')

        search = request.args.get('search', '').strip()
        farms = list(db.farms.find())
        sectors = []
        farms_for_select = []

        for farm in farms:
            farm['_id'] = str(farm['_id'])
            farms_for_select.append(farm)
            for sector in farm.get('sectors', []):
                sector['_id'] = str(sector.get('_id', ''))
                if search and search.lower() not in sector.get('name', '').lower():
                    continue
                sector['farm'] = farm
                sector['farm_id'] = farm['_id']
                sector['zone_count'] = len(sector.get('zones', []))
                sectors.append(sector)

        return render_template('sectors/index.html', sectors=sectors, farms=farms_for_select, search=search)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"sectors.index() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error: {err["message"]}', 'danger')
        return render_template('sectors/index.html', sectors=[], farms=[], search='')


@log_func_call
@admin_required
@sectors_bp.route('/add', methods=['POST'])
def add():
    try:
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('sectors.index'))

        farm_id = request.form.get('farm_id', '')
        if not farm_id:
            flash('Farm is required to add a sector', 'danger')
            return redirect(url_for('sectors.index'))

        farm = find_doc(db.farms, farm_id)
        if not farm:
            flash('Farm not found', 'danger')
            return redirect(url_for('sectors.index'))

        try:
            sector_data = SectorModel(
                sector_number=int(request.form.get('sector_number', len(farm.get('sectors', [])) + 1) or 1),
                name=request.form.get('name', ''),
                description=request.form.get('description', ''),
                location={
                    'area': {'value': float(request.form.get('area', 0) or 0), 'unit': request.form.get('area_unit', 'ha')},
                    'soil_type': request.form.get('soil_type', 'loam'),
                    'slope': request.form.get('slope', ''),
                    'irrigation_type': request.form.get('irrigation_type', '')
                },
                metadata={'status': 'active', 'notes': request.form.get('notes', '')}
            )

            sector_dict = sector_data.model_dump()
            sector_dict['_id'] = str(ObjectId())
            sector_dict['zones'] = []

            db.farms.update_one(
                {'_id': ObjectId(farm_id)},
                {'$push': {'sectors': sector_dict}, '$set': {'last_updated_at': datetime.utcnow()}}
            )
            log_message('info', f"Added sector: {sector_data.name}", session.get('user_id'), session.get('username'))
            flash('Sector added successfully!', 'success')
        except Exception as ve:
            flash(f'Validation error: {str(ve)}', 'danger')

        return redirect(url_for('sectors.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"sectors.add() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error adding sector: {err["message"]}', 'danger')
        return redirect(url_for('sectors.index'))


@log_func_call
@sectors_bp.route('/<sector_id>')
def detail(sector_id):
    try:
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))

        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            abort(500)

        farms = list(db.farms.find())
        for farm in farms:
            for sector in farm.get('sectors', []):
                if str(sector.get('_id', '')) == sector_id:
                    sector['_id'] = str(sector['_id'])
                    farm['_id'] = str(farm['_id'])
                    for zone in sector.get('zones', []):
                        zone['_id'] = str(zone.get('_id', ''))
                        zone['row_count'] = len(zone.get('rows', []))
                        for row in zone.get('rows', []):
                            row['_id'] = str(row.get('_id', ''))
                            row['tree_count'] = len(row.get('trees', []))
                    return render_template('sectors/detail.html', sector=sector, farm=farm, zones=sector.get('zones', []))

        abort(404)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"sectors.detail() line {err['line']}: {err['message']}\n{err['trace']}")
        abort(500)


@log_func_call
@admin_required
@sectors_bp.route('/<sector_id>/edit', methods=['POST'])
def edit(sector_id):
    try:
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('sectors.index'))

        farms = list(db.farms.find())
        for farm in farms:
            for sector in farm.get('sectors', []):
                if str(sector.get('_id', '')) == sector_id:
                    try:
                        boundary = sector.get('boundary', {'type': 'Polygon', 'coordinates': []})
                        boundary_str = request.form.get('boundary', '').strip()
                        if boundary_str:
                            try:
                                boundary = json.loads(boundary_str)
                            except Exception:
                                pass

                        sector_data = SectorModel(
                            sector_number=int(request.form.get('sector_number', sector.get('sector_number', 1)) or 1),
                            name=request.form.get('name', ''),
                            description=request.form.get('description', ''),
                            location={
                                'area': {'value': float(request.form.get('area', 0) or 0), 'unit': request.form.get('area_unit', 'ha')},
                                'soil_type': request.form.get('soil_type', 'loam'),
                                'slope': request.form.get('slope', ''),
                                'irrigation_type': request.form.get('irrigation_type', '')
                            },
                            boundary=boundary,
                            metadata={
                                'status': request.form.get('status', sector.get('metadata', {}).get('status', 'active')),
                                'notes': request.form.get('notes', sector.get('metadata', {}).get('notes', ''))
                            }
                        )

                        sector['sector_number'] = sector_data.sector_number
                        sector['name'] = sector_data.name
                        sector['description'] = sector_data.description
                        sector['location'] = sector_data.location
                        sector['boundary'] = sector_data.boundary
                        sector['metadata'] = sector_data.metadata

                        db.farms.update_one({'_id': farm['_id']}, {'$set': {'sectors': farm.get('sectors', []), 'last_updated_at': datetime.utcnow()}})
                        log_message('info', f"Updated sector: {sector_data.name}", session.get('user_id'), session.get('username'))
                        flash('Sector updated successfully!', 'success')
                    except Exception as ve:
                        flash(f'Validation error: {str(ve)}', 'danger')
                    return redirect(url_for('sectors.index'))

        flash('Sector not found', 'danger')
        return redirect(url_for('sectors.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"sectors.edit() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error editing sector: {err["message"]}', 'danger')
        return redirect(url_for('sectors.index'))


@log_func_call
@admin_required
@sectors_bp.route('/<sector_id>/delete', methods=['POST'])
def delete(sector_id):
    try:
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('sectors.index'))

        farms = list(db.farms.find())
        for farm in farms:
            sectors = farm.get('sectors', [])
            for i, sector in enumerate(sectors):
                if str(sector.get('_id', '')) == sector_id:
                    sector_name = sector.get('name', '')
                    sectors.pop(i)
                    db.farms.update_one({'_id': farm['_id']}, {'$set': {'sectors': sectors, 'last_updated_at': datetime.utcnow()}})
                    log_message('info', f"Deleted sector: {sector_name}", session.get('user_id'), session.get('username'))
                    flash('Sector deleted successfully!', 'success')
                    return redirect(url_for('sectors.index'))

        flash('Sector not found', 'danger')
        return redirect(url_for('sectors.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"sectors.delete() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error deleting sector: {err["message"]}', 'danger')
        return redirect(url_for('sectors.index'))


@log_func_call
@admin_required
@sectors_bp.route('/bulk_add', methods=['POST'])
def bulk_add():
    try:
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('sectors.index'))

        farm_id = request.form.get('farm_id', '')
        if not farm_id:
            flash('Farm is required to bulk add sectors', 'danger')
            return redirect(url_for('sectors.index'))

        farm = find_doc(db.farms, farm_id)
        if not farm:
            flash('Farm not found', 'danger')
            return redirect(url_for('sectors.index'))

        prefix = request.form.get('prefix', 'Sector').strip()
        start_from = int(request.form.get('start_from', 1) or 1)
        end_at = int(request.form.get('end_at', 5) or 5)
        names = [f"{prefix} {i}" for i in range(start_from, end_at + 1)]

        added_count = 0
        for idx, name in enumerate(names):
            try:
                sector_data = SectorModel(
                    sector_number=start_from + idx,
                    name=name,
                    description=request.form.get('description', ''),
                    location={
                        'area': {'value': float(request.form.get('area', 0) or 0), 'unit': request.form.get('area_unit', 'ha')},
                        'soil_type': request.form.get('soil_type', 'loam'),
                        'slope': request.form.get('slope', ''),
                        'irrigation_type': request.form.get('irrigation_type', '')
                    },
                    metadata={'status': 'active', 'notes': ''}
                )
                sector_dict = sector_data.model_dump()
                sector_dict['_id'] = ObjectId()
                sector_dict['zones'] = []
                farm.get('sectors', []).append(sector_dict)
                added_count += 1
            except Exception as ve:
                flash(f'Validation error for "{name}": {str(ve)}', 'danger')

        if added_count > 0:
            db.farms.update_one({'_id': farm['_id']}, {'$set': {'sectors': farm.get('sectors', []), 'last_updated_at': datetime.utcnow()}})
            log_message('info', f'Bulk added {added_count} sectors', session.get('user_id'), session.get('username'))
            flash(f'{added_count} sectors added successfully!', 'success')

        return redirect(url_for('sectors.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"sectors.bulk_add() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error bulk adding sectors: {err["message"]}', 'danger')
        return redirect(url_for('sectors.index'))
