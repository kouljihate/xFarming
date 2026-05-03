from flask import Blueprint, render_template, session, redirect, url_for, request
from app.database import get_db
import plotly.graph_objects as go
import plotly.offline as pyo
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
    
    # Generate Treemap
    lands = list(db.lands.find())
    labels = []
    parents = []
    values = []
    colors = []
    
    # Add root
    labels.append('xFarming')
    parents.append('')
    values.append(stats['trees'] or 1)
    colors.append('#1f77b4')
    
    # Add lands
    for land in lands:
        land_name = land.get('name', 'Unknown')
        labels.append(land_name)
        parents.append('xFarming')
        land_trees = db.trees.count_documents({'land_id': land['_id']})
        values.append(land_trees or 1)
        colors.append('#2ca02c')
        
        # Add sectors
        sectors = list(db.sectors.find({'land_id': land['_id']}))
        for sector in sectors:
            sector_name = sector.get('name', 'Unknown')
            labels.append(f"{land_name} - {sector_name}")
            parents.append(land_name)
            sector_trees = db.trees.count_documents({'sector_id': sector['_id']})
            values.append(sector_trees or 1)
            colors.append('#ff7f0e')
    
    if len(labels) > 1:
        fig = go.Figure(go.Treemap(
            labels=labels,
            parents=parents,
            values=values,
            marker_colors=colors,
            textinfo="label+value"
        ))
        fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=400)
        treemap = pyo.plot(fig, output_type='div', include_plotlyjs=False)
    else:
        treemap = None
    
    return render_template('dashboard/index.html', stats=stats, activities=recent_activities, treemap=treemap)

@dashboard_bp.route('/set-theme/<theme>')
def set_theme(theme):
    # Map legacy light/dark to Bootswatch themes
    theme_map = {
        'light': 'minty',
        'dark': 'darkly'
    }
    session['theme'] = theme_map.get(theme, theme)
    return redirect(request.referrer or url_for('dashboard.index'))
