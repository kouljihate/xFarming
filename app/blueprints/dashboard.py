import sys
import traceback
from flask import Blueprint, render_template, session, redirect, url_for, request
from app.database import get_db
from app.utils.logging import log_message, log_func_call
from app.utils.map_utils import build_farms_map
from app.utils.charts import (
    build_entity_totals_chart,
    build_farms_chart,
    build_sectors_zones_chart,
    build_trees_per_farm_chart,
)

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')
dashboard_bp.strict_slashes = False


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
@dashboard_bp.route('/')
def index():
    try:
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))

        lang = request.args.get('lang')
        if lang:
            session['lang'] = lang
            return redirect(url_for('dashboard.index'))

        db = get_db()
        if isinstance(db, dict) and db.get('error'):
            return f'Database error: {db["message"]}', 500

        farms = list(db.farms.find())
        stats = {
            'farms': len(farms),
            'sectors': 0,
            'zones': 0,
            'rows': 0,
            'trees': 0
        }

        farm_chart_data = []

        for farm in farms:
            sector_count = 0
            zone_count = 0
            row_count = 0
            tree_count = 0
            for sector in farm.get('sectors', []):
                sector_count += 1
                zone_count += len(sector.get('zones', []))
                for zone in sector.get('zones', []):
                    row_count += len(zone.get('rows', []))
                    for row in zone.get('rows', []):
                        tree_count += len(row.get('trees', []))
            stats['sectors'] += sector_count
            stats['zones'] += zone_count
            stats['rows'] += row_count
            stats['trees'] += tree_count
            farm_chart_data.append({
                'name': farm.get('farm_name', 'Unknown'),
                'sectors': sector_count,
                'zones': zone_count,
                'rows': row_count,
                'trees': tree_count,
            })

        recent_activities = list(db.activities.find().sort('date', -1).limit(10))
        map_html = build_farms_map(farms, height=500)

        chart_entity_totals = build_entity_totals_chart(stats)
        chart_farms = build_farms_chart(stats)
        chart_sectors_zones = build_sectors_zones_chart(farm_chart_data)
        chart_trees_per_farm = build_trees_per_farm_chart(farm_chart_data)

        return render_template(
            'dashboard/index.html',
            stats=stats,
            activities=recent_activities,
            map_html=map_html,
            chart_entity_totals=chart_entity_totals,
            chart_farms=chart_farms,
            chart_sectors_zones=chart_sectors_zones,
            chart_trees_per_farm=chart_trees_per_farm,
        )
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"dashboard.index() line {err['line']}: {err['message']}\n{err['trace']}")
        return f'Dashboard error: {err["message"]}', 500


@log_func_call
@dashboard_bp.route('/set-theme/<theme>')
def set_theme(theme):
    try:
        theme_map = {
            'light': 'minty',
            'dark': 'darkly'
        }
        session['theme'] = theme_map.get(theme, theme)
        return redirect(request.referrer or url_for('dashboard.index'))
    except Exception as e:
        err = _error_info(e)
        log_message('error', f"set_theme() line {err['line']}: {err['message']}\n{err['trace']}")
        return redirect(url_for('dashboard.index'))
