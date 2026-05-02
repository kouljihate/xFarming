from flask import Blueprint, render_template, session, redirect, url_for, request
from app.database import get_db
import folium

lands_bp = Blueprint('lands', __name__, url_prefix='/lands')

@lands_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    lands = list(db.lands.find())
    
    for land in lands:
        m = folium.Map(location=[land.get('latitude', 0), land.get('longitude', 0)], zoom_start=10, height='100px')
        folium.Marker([land.get('latitude', 0), land.get('longitude', 0)], popup=land['name']).add_to(m)
        land['map'] = m._repr_html_()
        
        land['sector_count'] = db.sectors.count_documents({'land_id': land['_id']})
    
    return render_template('lands/index.html', lands=lands)

@lands_bp.route('/<land_id>')
def detail(land_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    land = db.lands.find_one({'_id': land_id})
    
    if not land:
        return redirect(url_for('lands.index'))
    
    m = folium.Map(location=[land.get('latitude', 0), land.get('longitude', 0)], zoom_start=12, height='400px')
    folium.Marker([land.get('latitude', 0), land.get('longitude', 0)], popup=land['name']).add_to(m)
    land['map'] = m._repr_html_()
    
    sectors = list(db.sectors.find({'land_id': land_id}))
    for sector in sectors:
        sector['zones'] = list(db.zones.find({'sector_id': sector['_id']}))
        for zone in sector['zones']:
            zone['rows'] = list(db.rows.find({'zone_id': zone['_id']}))
            for row in zone['rows']:
                row['trees'] = list(db.trees.find({'row_id': row['_id']}))
    
    return render_template('lands/detail.html', land=land, sectors=sectors)
