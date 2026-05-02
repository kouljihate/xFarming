from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort
from app.database import get_db
from app.utils.logging import log_message
from bson import ObjectId
from datetime import datetime

sectors_bp = Blueprint('sectors', __name__, url_prefix='/sectors')
sectors_bp.strict_slashes = False

@sectors_bp.route('/<sector_id>')
def detail(sector_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    sector = db.sectors.find_one({'_id': ObjectId(sector_id)})
    if not sector:
        abort(404)
    
    sector['_id'] = str(sector['_id'])
    land = db.lands.find_one({'_id': sector['land_id']})
    
    zones = list(db.zones.find({'sector_id': ObjectId(sector_id)}))
    for zone in zones:
        zone['_id'] = str(zone['_id'])
        zone['rows'] = list(db.rows.find({'zone_id': ObjectId(zone['_id'])}))
        for row in zone['rows']:
            row['_id'] = str(row['_id'])
            row['tree_count'] = db.trees.count_documents({'row_id': ObjectId(row['_id'])})
    
    return render_template('sectors/detail.html', sector=sector, land=land, zones=zones)

@sectors_bp.route('/<sector_id>/edit', methods=['GET', 'POST'])
def edit(sector_id):
    if 'user_id' not in session or session.get('role') not in ['admin']:
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.detail', land_id=''))
    
    db = get_db()
    sector = db.sectors.find_one({'_id': ObjectId(sector_id)})
    if not sector:
        abort(404)
    
    if request.method == 'POST':
        new_name = request.form.get('name')
        db.sectors.update_one({'_id': ObjectId(sector_id)}, {'$set': {'name': new_name}})
        log_message('info', f'Updated sector name to {new_name}', session.get('user_id'), session.get('username'))
        flash('Sector updated successfully!', 'success')
        return redirect(url_for('sectors.detail', sector_id=sector_id))
    
    sector['_id'] = str(sector['_id'])
    return render_template('sectors/edit.html', sector=sector)

@sectors_bp.route('/<sector_id>/delete', methods=['POST'])
def delete(sector_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('lands.detail', land_id=''))
    
    db = get_db()
    sector = db.sectors.find_one({'_id': ObjectId(sector_id)})
    if sector:
        land_id = str(sector['land_id'])
        db.sectors.delete_one({'_id': ObjectId(sector_id)})
        log_message('warning', f'Deleted sector {sector["name"]}', session.get('user_id'), session.get('username'))
        flash('Sector deleted successfully!', 'success')
        return redirect(url_for('lands.detail', land_id=land_id))
    
    return redirect(url_for('lands.index'))
