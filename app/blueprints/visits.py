from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort, jsonify
from app.database import get_db
from app.utils.logging import log_message
from app.models.validation import VisitModel
from bson import ObjectId
from datetime import datetime

visits_bp = Blueprint('visits', __name__, url_prefix='/visits')
visits_bp.strict_slashes = False


@visits_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    search = request.args.get('search', '').strip()
    visit_type_filter = request.args.get('type', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    all_visits = []
    lands = list(db.lands.find())
    
    for land in lands:
        land_id = str(land['_id'])
        land_name = land.get('name', '')
        for farm in land.get('farms', []):
            farm_id = str(farm.get('_id', ''))
            farm_name = farm.get('name', '')
            for sector in farm.get('sectors', []):
                sector_id = str(sector.get('_id', ''))
                sector_name = sector.get('name', '')
                for zone in sector.get('zones', []):
                    zone_id = str(zone.get('_id', ''))
                    zone_name = zone.get('name', '')
                    for row in zone.get('rows', []):
                        row_id = str(row.get('_id', ''))
                        row_name = row.get('name', '')
                        for tree in row.get('trees', []):
                            tree_id = str(tree.get('_id', ''))
                            tree_name = tree.get('name', tree.get('tree_id', ''))
                            tree_variety = tree.get('basic_info', {}).get('variety', '')
                            
                            for visit in tree.get('visits', []):
                                visit['_id'] = str(visit.get('_id', ''))
                                
                                if search:
                                    search_lower = search.lower()
                                    if (search_lower not in tree_name.lower() and 
                                        search_lower not in tree_variety.lower() and
                                        search_lower not in visit.get('visit_type', '').lower()):
                                        continue
                                
                                if visit_type_filter and visit.get('visit_type', '') != visit_type_filter:
                                    continue
                                
                                visit['tree_id'] = tree_id
                                visit['tree_name'] = tree_name
                                visit['tree_variety'] = tree_variety
                                visit['row_id'] = row_id
                                visit['row_name'] = row_name
                                visit['zone_id'] = zone_id
                                visit['zone_name'] = zone_name
                                visit['sector_id'] = sector_id
                                visit['sector_name'] = sector_name
                                visit['farm_id'] = farm_id
                                visit['farm_name'] = farm_name
                                visit['land_id'] = land_id
                                visit['land_name'] = land_name
                                
                                all_visits.append(visit)
    
    all_visits.sort(key=lambda x: x.get('visit_date', ''), reverse=True)
    
    total = len(all_visits)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_visits = all_visits[start:end]
    
    return render_template('visits/index.html', 
                           visits=paginated_visits, 
                           page=page, 
                           per_page=per_page, 
                           total=total,
                           search=search,
                           visit_type_filter=visit_type_filter)


@visits_bp.route('/add', methods=['POST'])
def add():
    if 'user_id' not in session or session.get('role') not in ['admin', 'worker']:
        flash('Permission denied', 'danger')
        return redirect(url_for('visits.index'))
    
    db = get_db()
    tree_id = request.form.get('tree_id')
    land_id = request.form.get('land_id')
    
    try:
        visit_data = VisitModel(
            visit_id=request.form.get('visit_id', '').strip(),
            visit_date=request.form.get('visit_date', datetime.now().strftime('%Y-%m-%d')),
            visit_type=request.form.get('visit_type', 'inspection'),
            inspector=request.form.get('inspector', ''),
            status=request.form.get('status', 'pending'),
            findings={
                'health_status': request.form.get('health_status', ''),
                'pests': request.form.get('pests', ''),
                'diseases': request.form.get('diseases', ''),
                'notes': request.form.get('findings_notes', '')
            },
            next_visit=request.form.get('next_visit', ''),
            metadata={
                'created_date': datetime.now().isoformat(),
                'status': 'active'
            }
        )
        
        lands = list(db.lands.find())
        for land in lands:
            if str(land['_id']) == land_id:
                for farm in land.get('farms', []):
                    for sector in farm.get('sectors', []):
                        for zone in sector.get('zones', []):
                            for row in zone.get('rows', []):
                                for tree in row.get('trees', []):
                                    if str(tree.get('_id', '')) == tree_id:
                                        if 'visits' not in tree:
                                            tree['visits'] = []
                                        visit_dict = visit_data.model_dump()
                                        visit_dict['_id'] = str(ObjectId())
                                        tree['visits'].append(visit_dict)
                                        db.lands.update_one({'_id': land['_id']}, 
                                                           {'$set': {'farms': land.get('farms', [])}})
                                        log_message('info', f"Added visit to tree: {tree.get('name', tree_id)}", 
                                                   session.get('user_id'), session.get('username'))
                                        flash('Visit added successfully!', 'success')
                                        return redirect(url_for('visits.index'))
    except Exception as e:
        flash(f'Validation error: {str(e)}', 'danger')
    
    return redirect(url_for('visits.index'))


@visits_bp.route('/<visit_id>')
def detail(visit_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    lands = list(db.lands.find())
    
    for land in lands:
        for farm in land.get('farms', []):
            for sector in farm.get('sectors', []):
                for zone in sector.get('zones', []):
                    for row in zone.get('rows', []):
                        for tree in row.get('trees', []):
                            for visit in tree.get('visits', []):
                                if visit.get('_id') == visit_id:
                                    visit['tree'] = tree
                                    visit['row'] = row
                                    visit['zone'] = zone
                                    visit['sector'] = sector
                                    visit['farm'] = farm
                                    visit['land'] = land
                                    return render_template('visits/detail.html', visit=visit)
    
    abort(404)


@visits_bp.route('/<visit_id>/edit', methods=['GET', 'POST'])
def edit(visit_id):
    if 'user_id' not in session or session.get('role') not in ['admin', 'worker']:
        flash('Permission denied', 'danger')
        return redirect(url_for('visits.index'))
    
    db = get_db()
    lands = list(db.lands.find())
    
    for land in lands:
        for farm in land.get('farms', []):
            for sector in farm.get('sectors', []):
                for zone in sector.get('zones', []):
                    for row in zone.get('rows', []):
                        for tree in row.get('trees', []):
                            for visit in tree.get('visits', []):
                                if visit.get('_id') == visit_id:
                                    if request.method == 'POST':
                                        try:
                                            visit['visit_id'] = request.form.get('visit_id', visit.get('visit_id', ''))
                                            visit['visit_date'] = request.form.get('visit_date', visit.get('visit_date', ''))
                                            visit['visit_type'] = request.form.get('visit_type', visit.get('visit_type', 'inspection'))
                                            visit['inspector'] = request.form.get('inspector', visit.get('inspector', ''))
                                            visit['status'] = request.form.get('status', visit.get('status', 'pending'))
                                            
                                            if 'findings' not in visit:
                                                visit['findings'] = {}
                                            visit['findings']['health_status'] = request.form.get('health_status', visit.get('findings', {}).get('health_status', ''))
                                            visit['findings']['pests'] = request.form.get('pests', visit.get('findings', {}).get('pests', ''))
                                            visit['findings']['diseases'] = request.form.get('diseases', visit.get('findings', {}).get('diseases', ''))
                                            visit['findings']['notes'] = request.form.get('findings_notes', visit.get('findings', {}).get('notes', ''))
                                            
                                            visit['next_visit'] = request.form.get('next_visit', visit.get('next_visit', ''))
                                            
                                            if 'metadata' not in visit:
                                                visit['metadata'] = {}
                                            visit['metadata']['last_updated'] = datetime.now().isoformat()
                                            
                                            db.lands.update_one({'_id': land['_id']}, 
                                                               {'$set': {'farms': land.get('farms', [])}})
                                            log_message('info', f"Updated visit: {visit_id}", 
                                                       session.get('user_id'), session.get('username'))
                                            flash('Visit updated successfully!', 'success')
                                        except Exception as e:
                                            flash(f'Validation error: {str(e)}', 'danger')
                                        return redirect(url_for('visits.index'))
                                    else:
                                        return render_template('visits/edit.html', visit=visit, tree=tree)
    
    abort(404)


@visits_bp.route('/<visit_id>/delete', methods=['POST'])
def delete(visit_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('visits.index'))
    
    db = get_db()
    lands = list(db.lands.find())
    
    for land in lands:
        for farm in land.get('farms', []):
            for sector in farm.get('sectors', []):
                for zone in sector.get('zones', []):
                    for row in zone.get('rows', []):
                        for tree in row.get('trees', []):
                            visits = tree.get('visits', [])
                            for i, visit in enumerate(visits):
                                if visit.get('_id') == visit_id:
                                    visits.pop(i)
                                    db.lands.update_one({'_id': land['_id']}, 
                                                       {'$set': {'farms': land.get('farms', [])}})
                                    log_message('info', f"Deleted visit: {visit_id}", 
                                               session.get('user_id'), session.get('username'))
                                    flash('Visit deleted successfully!', 'success')
                                    return redirect(url_for('visits.index'))
    
    flash('Visit not found', 'danger')
    return redirect(url_for('visits.index'))