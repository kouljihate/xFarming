from flask import Blueprint, render_template, session, redirect, url_for, request
import json

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')
dashboard_bp.strict_slashes = False

@dashboard_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    # Handle language change
    lang = request.args.get('lang')
    if lang:
        session['lang'] = lang
        return redirect(url_for('dashboard.index'))
    
    db = get_db()
    
    stats = {
        'lands': db.lands.count_documents({}),
        'sectors': db.sectors.count_documents({}),
        'zones': db.zones.count_documents({}),
        'rows': db.rows.count_documents({}),
        'trees': db.trees.count_documents({})
    }
    
    recent_activities = list(db.activities.find().sort('date', -1).limit(10))
    
    # Get all lands for the map
    lands = list(db.lands.find())
    
    # Prepare lands data for JSON
    lands_data = []
    for land in lands:
        lat = land.get('latitude')
        lng = land.get('longitude')
        if lat is None or lng is None:
            continue
        try:
            lat_f = float(lat)
            lng_f = float(lng)
            sector_count = db.sectors.count_documents({'land_id': land['_id']})
            lands_data.append({
                'name': land.get('name', 'Unknown'),
                'lat': lat_f,
                'lng': lng_f,
                'soil_type': land.get('soil_type', 'N/A'),
                'area': land.get('area', 'N/A'),
                'sectors': sector_count,
                'boundaries': land.get('boundaries') if land.get('boundaries') else None
            })
        except (ValueError, TypeError):
            continue
    
    lands_json = json.dumps(lands_data)
    
    return render_template('dashboard/index.html', stats=stats, activities=recent_activities, lands_json=lands_json, lands_count=len(lands))

@dashboard_bp.route('/set-theme/<theme>')
def set_theme(theme):
    # Map legacy light/dark to Bootswatch themes
    theme_map = {
        'light': 'minty',
        'dark': 'darkly'
    }
    session['theme'] = theme_map.get(theme, theme)
    return redirect(request.referrer or url_for('dashboard.index'))
