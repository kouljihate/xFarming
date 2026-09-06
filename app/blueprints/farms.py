import sys
import traceback
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort, jsonify
from app.database import get_db, find_doc
from app.utils.logging import log_message, log_func_call, login_required, admin_required
from app.utils.calculation import calculate_polygon_metrics, calculate_centroid, parse_simple_coordinates
from app.utils.map_utils import build_farm_edit_map, build_farms_map, get_altitude_meters
from app.models.validation import FarmModel, SectorModel, ZoneModel, RowModel, TreeModel
from bson import ObjectId
from datetime import datetime
import json


farms_bp = Blueprint('farms', __name__, url_prefix='/farms')
farms_bp.strict_slashes = False


@farms_bp.route('/api/altitude')
def api_altitude():
    try:
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        if lat is None or lon is None:
            return jsonify({'error': 'lat and lon are required'}), 400
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return jsonify({'error': 'Invalid coordinates'}), 400
        altitude = get_altitude_meters(lat, lon)
        if altitude is None:
            return jsonify({'error': 'Could not determine altitude'}), 404
        return jsonify({'altitude': round(altitude, 2)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@farms_bp.route('/api/calculate')
def api_calculate():
    try:
        coords_str = request.args.get('coords', '').strip()
        if not coords_str:
            return jsonify({'error': 'Coordinates are required'}), 400
        coords = parse_simple_coordinates(coords_str)
        if coords is None:
            return jsonify({'error': 'Invalid coordinate format. Use: [(lat, lon), (lat, lon), ...]'}), 400
        if isinstance(coords, dict) and coords.get('error'):
            return jsonify({'error': coords['error']}), 400
        metrics = calculate_polygon_metrics(coords)
        if isinstance(metrics, dict) and metrics.get('error'):
            return jsonify({'error': metrics['error']}), 400
        centroid = calculate_centroid(coords)
        if isinstance(centroid, dict) and centroid.get('error'):
            return jsonify({'error': centroid['error']}), 400
        return jsonify({
            'area_ha': round(metrics.get('area_ha', 0), 4),
            'perimeter_m': round(metrics.get('perimeter_m', 0), 2),
            'center_lat': centroid.get('latitude'),
            'center_lon': centroid.get('longitude'),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
@login_required
@farms_bp.route('/')
def index():
    try:
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return render_template('farms/index.html', farms=[], search='')

        search = request.args.get('search', '').strip()
        query = {}
        if search:
            query['farm_name'] = {'$regex': search, '$options': 'i'}

        farms = list(db.farms.find(query))
        for farm in farms:
            farm['_id'] = str(farm['_id'])
            farm['sector_count'] = len(farm.get('sectors', []))
            zone_count = 0
            row_count = 0
            tree_count = 0
            for sector in farm.get('sectors', []):
                zone_count += len(sector.get('zones', []))
                for zone in sector.get('zones', []):
                    row_count += len(zone.get('rows', []))
                    for row in zone.get('rows', []):
                        tree_count += len(row.get('trees', []))
            farm['zone_count'] = zone_count
            farm['row_count'] = row_count
            farm['tree_count'] = tree_count

        map_html = build_farms_map(farms, height=400)
        return render_template('farms/index.html', farms=farms, search=search, map_html=map_html, form_data={})
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"farms.index() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error: {err["message"]}', 'danger')
        return render_template('farms/index.html', farms=[], search='')


@log_func_call
@admin_required
@farms_bp.route('/add', methods=['POST'])
def add():
    try:
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('farms.index'))

        action = request.form.get('action', 'save')

        farm_name = request.form.get('farm_name', '').strip()
        description = request.form.get('description', '')
        street = request.form.get('street', '')
        city = request.form.get('city', '')
        latitude_str = request.form.get('latitude', '')
        longitude_str = request.form.get('longitude', '')
        altitude_str = request.form.get('altitude', '0')
        coordinates_str = request.form.get('coordinates', '').strip()

        latitude = 0.0
        longitude = 0.0
        altitude = 0.0
        address = {'street': street, 'city': city, 'state': '', 'postal_code': '', 'country': ''}

        if latitude_str and longitude_str:
            try:
                latitude = float(latitude_str)
                longitude = float(longitude_str)
                if (not street or not city) and latitude != 0.0 and longitude != 0.0:
                    from app.utils.map_utils import latlon_to_dms_and_address
                    try:
                        addr_info = latlon_to_dms_and_address(latitude, longitude)
                        addr = addr_info.get('address', '')
                        if addr:
                            if not street:
                                address['street'] = addr.split(',')[0].strip()
                            if not city:
                                parts = addr.split(',')
                                if len(parts) >= 2:
                                    address['city'] = parts[1].strip()
                    except Exception:
                        pass
                altitude_val = float(altitude_str) if altitude_str else 0.0
                if altitude_val == 0.0:
                    try:
                        from app.utils.map_utils import get_altitude_meters
                        alt = get_altitude_meters(latitude, longitude)
                        if alt is not None:
                            altitude_val = alt
                    except Exception:
                        pass
                altitude = altitude_val
            except ValueError:
                pass

        try:
            altitude = float(altitude_str) if altitude_str else 0.0
        except ValueError:
            altitude = 0.0

        boundary = {'type': 'Polygon', 'coordinates': []}
        boundary_str = request.form.get('boundary', '').strip()
        if boundary_str:
            try:
                boundary = json.loads(boundary_str)
            except Exception:
                pass

        farm_data = FarmModel(
            farm_name=farm_name,
            description=description,
            address=address,
            center_coordinate={'latitude': latitude, 'longitude': longitude},
            altitude=altitude,
            location={
                'area': {'value': float(request.form.get('area', 0) or 0), 'unit': request.form.get('area_unit', 'ha')},
                'soil_type': request.form.get('soil_type', 'loam'),
                'topography': request.form.get('topography', ''),
                'climate_zone': request.form.get('climate_zone', '')
            },
            boundary=boundary,
            irrigation_system={
                'type': request.form.get('irrigation_type', ''),
                'source': request.form.get('irrigation_source', ''),
                'capacity_lph': int(request.form.get('irrigation_capacity', 0) or 0),
                'notes': request.form.get('irrigation_notes', '')
            },
            legal={
                'registration_number': request.form.get('registration_number', ''),
                'lease_status': request.form.get('lease_status', 'owned'),
                'lease_expiry': request.form.get('lease_expiry', ''),
                'documents': request.form.get('legal_docs', '')
            },
            metadata={
                'established_date': request.form.get('established_date', ''),
                'last_updated': '',
                'status': request.form.get('status', 'active'),
                'notes': request.form.get('notes', ''),
                'version': 1
            }
        )

        FarmModel.check_duplicate(db, farm_data.farm_name)

        farm_dict = farm_data.model_dump()
        farm_dict['_id'] = ObjectId()
        farm_dict['sectors'] = []
        farm_dict['created_at'] = datetime.utcnow()
        farm_dict['last_updated_at'] = datetime.utcnow()

        db.farms.insert_one(farm_dict)
        log_message('info', f"Added farm: {farm_data.farm_name}", session.get('user_id'), session.get('username'))
        flash('Farm added successfully!', 'success')
        return redirect(url_for('farms.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"farms.add() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error: {err["message"]}', 'danger')
        return redirect(url_for('farms.index'))


@log_func_call
@login_required
@farms_bp.route('/<farm_id>')
def detail(farm_id):
    try:
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            abort(500)

        farm = find_doc(db.farms, farm_id)
        if not farm:
            abort(404)

        farm['_id'] = str(farm['_id'])
        sectors = farm.get('sectors', [])
        for sector in sectors:
            sector['_id'] = str(sector.get('_id', ''))
            sector['zone_count'] = len(sector.get('zones', []))
            for zone in sector.get('zones', []):
                zone['_id'] = str(zone.get('_id', ''))
                zone['row_count'] = len(zone.get('rows', []))
                for row in zone.get('rows', []):
                    row['_id'] = str(row.get('_id', ''))
                    row['tree_count'] = len(row.get('trees', []))

        map_html = build_farm_edit_map(farm, height=400)
        return render_template('farms/detail.html', farm=farm, sectors=sectors, map_html=map_html)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"farms.detail() line {err['line']}: {err['message']}\n{err['trace']}")
        abort(500)


@log_func_call
@admin_required
@farms_bp.route('/<farm_id>/edit', methods=['GET', 'POST'])
def edit(farm_id):
    try:
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('farms.index'))

        farm = find_doc(db.farms, farm_id)
        if not farm:
            abort(404)

        if request.method == 'POST':
            try:
                farm_name = request.form.get('farm_name', farm.get('farm_name', ''))
                description = request.form.get('description', farm.get('description', ''))

                address = {
                    'street': request.form.get('street', farm.get('address', {}).get('street', '')),
                    'city': request.form.get('city', farm.get('address', {}).get('city', '')),
                    'state': request.form.get('state', farm.get('address', {}).get('state', '')),
                    'postal_code': request.form.get('postal_code', farm.get('address', {}).get('postal_code', '')),
                    'country': request.form.get('country', farm.get('address', {}).get('country', ''))
                }

                try:
                    latitude = float(request.form.get('latitude', farm.get('center_coordinate', {}).get('latitude', 0)))
                    longitude = float(request.form.get('longitude', farm.get('center_coordinate', {}).get('longitude', 0)))
                except (ValueError, TypeError):
                    latitude = farm.get('center_coordinate', {}).get('latitude', 0)
                    longitude = farm.get('center_coordinate', {}).get('longitude', 0)

                try:
                    altitude = float(request.form.get('altitude', farm.get('altitude', 0)))
                except (ValueError, TypeError):
                    altitude = farm.get('altitude', 0)

                boundary = farm.get('boundary', {'type': 'Polygon', 'coordinates': []})
                boundary_str = request.form.get('boundary', '').strip()
                if boundary_str:
                    try:
                        boundary = json.loads(boundary_str)
                    except Exception:
                        pass

                farm_data = FarmModel(
                    farm_id=farm.get('farm_id', ''),
                    farm_name=farm_name,
                    description=description,
                    address=address,
                    center_coordinate={'latitude': latitude, 'longitude': longitude},
                    altitude=altitude,
                    location={
                        'area': {'value': float(request.form.get('area', 0) or 0), 'unit': request.form.get('area_unit', 'ha')},
                        'soil_type': request.form.get('soil_type', farm.get('location', {}).get('soil_type', '')),
                        'topography': request.form.get('topography', farm.get('location', {}).get('topography', '')),
                        'climate_zone': request.form.get('climate_zone', farm.get('location', {}).get('climate_zone', ''))
                    },
                    boundary=boundary,
                    irrigation_system={
                        'type': request.form.get('irrigation_type', farm.get('irrigation_system', {}).get('type', '')),
                        'source': request.form.get('irrigation_source', farm.get('irrigation_system', {}).get('source', '')),
                        'capacity_lph': int(request.form.get('irrigation_capacity', farm.get('irrigation_system', {}).get('capacity_lph', 0)) or 0),
                        'notes': request.form.get('irrigation_notes', farm.get('irrigation_system', {}).get('notes', ''))
                    },
                    legal={
                        'registration_number': request.form.get('registration_number', farm.get('legal', {}).get('registration_number', '')),
                        'lease_status': request.form.get('lease_status', farm.get('legal', {}).get('lease_status', 'owned')),
                        'lease_expiry': request.form.get('lease_expiry', farm.get('legal', {}).get('lease_expiry', '')),
                        'documents': request.form.get('legal_docs', farm.get('legal', {}).get('documents', ''))
                    },
                    metadata={
                        'established_date': request.form.get('established_date', farm.get('metadata', {}).get('established_date', '')),
                        'last_updated': datetime.utcnow().isoformat(),
                        'status': request.form.get('status', farm.get('metadata', {}).get('status', 'active')),
                        'notes': request.form.get('notes', farm.get('metadata', {}).get('notes', '')),
                        'version': farm.get('metadata', {}).get('version', 1)
                    }
                )

                db.farms.update_one(
                    {'_id': farm['_id']},
                    {'$set': {
                        'farm_name': farm_data.farm_name,
                        'description': farm_data.description,
                        'address': farm_data.address,
                        'center_coordinate': farm_data.center_coordinate,
                        'altitude': farm_data.altitude,
                        'location': farm_data.location,
                        'boundary': farm_data.boundary,
                        'irrigation_system': farm_data.irrigation_system,
                        'legal': farm_data.legal,
                        'metadata': farm_data.metadata,
                        'last_updated_at': datetime.utcnow()
                    }}
                )
                log_message('info', f"Updated farm: {farm_data.farm_name}", session.get('user_id'), session.get('username'))
                flash('Farm updated successfully!', 'success')
            except Exception as ve:
                flash(f'Validation error: {str(ve)}', 'danger')
            return redirect(url_for('farms.detail', farm_id=farm_id))
        else:
            farm['_id'] = str(farm['_id'])
            map_html = build_farm_edit_map(farm, height=300)
            return render_template('farms/edit.html', farm=farm, map_html=map_html)
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"farms.edit() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error editing farm: {err["message"]}', 'danger')
        return redirect(url_for('farms.index'))


@log_func_call
@admin_required
@farms_bp.route('/<farm_id>/delete', methods=['POST'])
def delete(farm_id):
    try:
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('farms.index'))

        log_message('info', f"Attempting to delete farm: {farm_id}", session.get('user_id'), session.get('username'))

        farm = find_doc(db.farms, farm_id)

        if farm:
            result = db.farms.delete_one({'_id': farm['_id']})
            if result.deleted_count > 0:
                log_message('info', f"Deleted farm: {farm.get('farm_name', '')} (id={farm_id})", session.get('user_id'), session.get('username'))
                flash('Farm deleted successfully!', 'success')
            else:
                log_message('error', f"delete_one returned deleted_count=0 for farm: {farm_id}", session.get('user_id'), session.get('username'))
                flash('Error: Farm could not be deleted.', 'danger')
        else:
            log_message('error', f"Farm not found: {farm_id}", session.get('user_id'), session.get('username'))
            flash(f'Farm not found with ID: {farm_id}', 'danger')

        return redirect(url_for('farms.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"farms.delete() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error deleting farm: {err["message"]}', 'danger')
        return redirect(url_for('farms.index'))


@log_func_call
@admin_required
@farms_bp.route('/<farm_id>/add_sector', methods=['POST'])
def add_sector(farm_id):
    try:
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('farms.index'))

        farm = find_doc(db.farms, farm_id)
        if not farm:
            flash('Farm not found', 'danger')
            return redirect(url_for('farms.index'))

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
        sector_dict['_id'] = ObjectId()
        sector_dict['zones'] = []

        db.farms.update_one(
            {'_id': farm['_id']},
            {'$push': {'sectors': sector_dict}, '$set': {'last_updated_at': datetime.utcnow()}}
        )
        log_message('info', f"Added sector: {sector_data.name}", session.get('user_id'), session.get('username'))
        flash('Sector added successfully!', 'success')
        return redirect(url_for('farms.detail', farm_id=farm_id))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"farms.add_sector() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error adding sector: {err["message"]}', 'danger')
        return redirect(url_for('farms.detail', farm_id=farm_id))


@log_func_call
@admin_required
@farms_bp.route('/<farm_id>/add_zone', methods=['POST'])
def add_zone(farm_id):
    try:
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('farms.index'))

        farm = find_doc(db.farms, farm_id)
        if not farm:
            flash('Farm not found', 'danger')
            return redirect(url_for('farms.index'))

        sector_id = request.form.get('sector_id', '')

        zone_data = ZoneModel(
            zone_number=request.form.get('zone_number', ''),
            name=request.form.get('name', ''),
            description=request.form.get('description', ''),
            location={
                'area': {'value': float(request.form.get('area', 0) or 0), 'unit': request.form.get('area_unit', 'ha')},
                'row_spacing': {'value': float(request.form.get('row_spacing', 0) or 0), 'unit': 'feet'},
                'tree_spacing': {'value': float(request.form.get('tree_spacing', 0) or 0), 'unit': 'feet'},
                'orientation': request.form.get('orientation', '')
            },
            metadata={'status': 'active', 'notes': request.form.get('notes', '')}
        )

        zone_dict = zone_data.model_dump()
        zone_dict['_id'] = ObjectId()
        zone_dict['rows'] = []

        for sector in farm.get('sectors', []):
            if str(sector.get('_id', '')) == sector_id:
                if 'zones' not in sector:
                    sector['zones'] = []
                sector['zones'].append(zone_dict)
                break

        db.farms.update_one(
            {'_id': farm['_id']},
            {'$set': {'sectors': farm.get('sectors', []), 'last_updated_at': datetime.utcnow()}}
        )
        log_message('info', f"Added zone: {zone_data.name}", session.get('user_id'), session.get('username'))
        flash('Zone added successfully!', 'success')
        return redirect(url_for('farms.detail', farm_id=farm_id))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"farms.add_zone() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error adding zone: {err["message"]}', 'danger')
        return redirect(url_for('farms.detail', farm_id=farm_id))


@log_func_call
@admin_required
@farms_bp.route('/<farm_id>/add_row', methods=['POST'])
def add_row(farm_id):
    try:
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('farms.index'))

        farm = find_doc(db.farms, farm_id)
        if not farm:
            flash('Farm not found', 'danger')
            return redirect(url_for('farms.index'))

        zone_id = request.form.get('zone_id', '')

        row_data = RowModel(
            row_number=int(request.form.get('row_number', 1) or 1),
            name=request.form.get('name', ''),
            description=request.form.get('description', ''),
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
                    break

        db.farms.update_one(
            {'_id': farm['_id']},
            {'$set': {'sectors': farm.get('sectors', []), 'last_updated_at': datetime.utcnow()}}
        )
        log_message('info', f"Added row: {row_data.name}", session.get('user_id'), session.get('username'))
        flash('Row added successfully!', 'success')
        return redirect(url_for('farms.detail', farm_id=farm_id))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"farms.add_row() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error adding row: {err["message"]}', 'danger')
        return redirect(url_for('farms.detail', farm_id=farm_id))


@log_func_call
@admin_required
@farms_bp.route('/<farm_id>/add_tree', methods=['POST'])
def add_tree(farm_id):
    try:
        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            flash(f'Database error: {db["message"]}', 'danger')
            return redirect(url_for('farms.index'))

        farm = find_doc(db.farms, farm_id)
        if not farm:
            flash('Farm not found', 'danger')
            return redirect(url_for('farms.index'))

        row_id = request.form.get('row_id', '')

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
        tree_dict['_id'] = ObjectId()
        tree_dict['name'] = request.form.get('name', 'Tree')

        for sector in farm.get('sectors', []):
            for zone in sector.get('zones', []):
                for row in zone.get('rows', []):
                    if str(row.get('_id', '')) == row_id:
                        if 'trees' not in row:
                            row['trees'] = []
                        row['trees'].append(tree_dict)
                        break

        db.farms.update_one(
            {'_id': farm['_id']},
            {'$set': {'sectors': farm.get('sectors', []), 'last_updated_at': datetime.utcnow()}}
        )
        log_message('info', f"Added tree: {tree_dict.get('name', '')}", session.get('user_id'), session.get('username'))
        flash('Tree added successfully!', 'success')
        return redirect(url_for('farms.detail', farm_id=farm_id))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"farms.add_tree() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Error adding tree: {err["message"]}', 'danger')
        return redirect(url_for('farms.detail', farm_id=farm_id))
