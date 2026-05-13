from flask import Blueprint, render_template, session, redirect, url_for, request
from app.database import get_db
from app.utils.logging import log_message, log_func_call
import plotly.graph_objects as go
import plotly.offline as pyo

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')
dashboard_bp.strict_slashes = False

@log_func_call
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
    
    # Count embedded documents from lands collection
    lands = list(db.lands.find())
    stats = {
        'lands': len(lands),
        'farms': 0,
        'sectors': 0,
        'zones': 0,
        'rows': 0,
        'trees': 0
    }
    
    for land in lands:
        stats['farms'] += len(land.get('farms', []))
        for farm in land.get('farms', []):
            stats['sectors'] += len(farm.get('sectors', []))
            for sector in farm.get('sectors', []):
                stats['zones'] += len(sector.get('zones', []))
                for zone in sector.get('zones', []):
                    stats['rows'] += len(zone.get('rows', []))
                    for row in zone.get('rows', []):
                        stats['trees'] += len(row.get('trees', []))
    
    recent_activities = list(db.activities.find().sort('date', -1).limit(10))
    
    # Generate Plotly Mapbox of ALL Lands
    lands = list(db.lands.find())
    
    lats = []
    lngs = []
    texts = []
    custom_data = []
    
    for land in lands:
        # Coordinates are nested in location.coordinates
        location = land.get('location', {})
        coordinates = location.get('coordinates', {})
        lat = coordinates.get('latitude')
        lng = coordinates.get('longitude')
        
        if lat is None or lng is None:
            continue
        try:
            lat_f = float(lat)
            lng_f = float(lng)
            lats.append(lat_f)
            lngs.append(lng_f)
            texts.append(land.get('name', 'Unknown'))
            sector_count = db.sectors.count_documents({'land_id': land['_id']})
            # Get area from nested structure
            total_area = land.get('location', {}).get('total_area', {})
            area = total_area.get('value', 'N/A') if isinstance(total_area, dict) else 'N/A'
            custom_data.append([land.get('soil_type', 'N/A'), area, sector_count])
        except (ValueError, TypeError):
            continue
    
    if lats:
        fig = go.Figure(go.Scattermapbox(
            lat=lats,
            lon=lngs,
            mode='markers',
            marker=go.scattermapbox.Marker(
                size=14,
                color='green'
            ),
            text=texts,
            customdata=custom_data,
            hovertemplate='<b>%{text}</b><br>' +
                         'Soil Type: %{customdata[0]}<br>' +
                         'Area: %{customdata[1]} ha<br>' +
                         'Sectors: %{customdata[2]}<br>' +
                         '<extra></extra>'
        ))
        
        fig.update_layout(
            mapbox=dict(
                style='open-street-map',
                center=dict(lat=sum(lats)/len(lats), lon=sum(lngs)/len(lngs)),
                zoom=10
            ),
            margin=dict(t=10, l=10, r=10, b=10),
            height=500
        )
        
        map_html = pyo.plot(fig, output_type='div', include_plotlyjs=True)
    else:
        map_html = None
    
    return render_template('dashboard/index.html', stats=stats, activities=recent_activities, map_html=map_html)

@log_func_call
@dashboard_bp.route('/set-theme/<theme>')
def set_theme(theme):
    # Map legacy light/dark to Bootswatch themes
    theme_map = {
        'light': 'minty',
        'dark': 'darkly'
    }
    session['theme'] = theme_map.get(theme, theme)
    return redirect(request.referrer or url_for('dashboard.index'))
