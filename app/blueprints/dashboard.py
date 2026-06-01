import sys
import traceback
from flask import Blueprint, render_template, session, redirect, url_for, request
from app.database import get_db
from app.utils.logging import log_message, log_func_call
from app.utils.map_utils import build_lands_map

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
        map_html = build_lands_map(lands, height=500)
        
        return render_template('dashboard/index.html', stats=stats, activities=recent_activities, map_html=map_html)
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
