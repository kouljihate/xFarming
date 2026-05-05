from flask import Blueprint, render_template, session, redirect, url_for, request
import plotly.graph_objects as go
import plotly.offline as pyo

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
    
    # Generate Plotly Mapbox of ALL Lands
    lands = list(db.lands.find())
    
    lats = []
    lngs = []
    texts = []
    custom_data = []
    
    for land in lands:
        lat = land.get('latitude')
        lng = land.get('longitude')
        if lat is None or lng is None:
            continue
        try:
            lat_f = float(lat)
            lng_f = float(lng)
            lats.append(lat_f)
            lngs.append(lng_f)
            texts.append(land.get('name', 'Unknown'))
            sector_count = db.sectors.count_documents({'land_id': land['_id']})
            custom_data.append([land.get('soil_type', 'N/A'), land.get('area', 'N/A'), sector_count])
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
                         'Area: %{customdata[1]} acres<br>' +
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

@dashboard_bp.route('/set-theme/<theme>')
def set_theme(theme):
    # Map legacy light/dark to Bootswatch themes
    theme_map = {
        'light': 'minty',
        'dark': 'darkly'
    }
    session['theme'] = theme_map.get(theme, theme)
    return redirect(request.referrer or url_for('dashboard.index'))
