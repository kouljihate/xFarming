import sys
import traceback
import plotly.graph_objects as go
import plotly.offline as pyo
import plotly.express as px


def _error_info(e):
    tb = sys.exc_info()[-1]
    return {
        'error': True,
        'message': str(e),
        'function': sys._getframe(1).f_code.co_name,
        'line': tb.tb_lineno if tb else 0,
        'trace': traceback.format_exc()
    }


def _theme_layout(title=None, height=300):
    return dict(
        template='plotly_white',
        margin=dict(t=40, l=10, r=10, b=40),
        height=height,
        hovermode='x unified',
        title=dict(text=title, font=dict(size=14)) if title else None,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )


COLORS = px.colors.qualitative.Set2


def build_entity_totals_chart(stats):
    try:
        labels = ['Farms', 'Sectors', 'Zones', 'Rows', 'Trees']
        values = [stats.get(k, 0) for k in ['farms', 'sectors', 'zones', 'rows', 'trees']]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=labels,
            y=values,
            marker_color=COLORS[:5],
            text=values,
            textposition='outside',
            textfont=dict(size=12),
        ))
        fig.update_layout(**_theme_layout('Entity Totals', height=280))
        fig.update_yaxes(visible=False, showgrid=False)
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
    except Exception:
        return None


def build_farms_chart(stats):
    try:
        labels = ['Farms']
        values = [stats.get('farms', 0)]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=labels,
            y=values,
            marker_color=COLORS[0],
            text=values,
            textposition='outside',
            textfont=dict(size=12),
        ))
        fig.update_layout(**_theme_layout('Total Farms', height=280))
        fig.update_yaxes(visible=False, showgrid=False)
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
    except Exception:
        return None


def build_sectors_zones_chart(farm_data):
    try:
        names = [d['name'] for d in farm_data if d['sectors'] > 0]
        sectors = [d['sectors'] for d in farm_data if d['sectors'] > 0]
        zones = [d['zones'] for d in farm_data if d['sectors'] > 0]
        if not names:
            return None
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=names, y=sectors, name='Sectors',
            marker_color=COLORS[1], text=sectors, textposition='outside', textfont=dict(size=10),
        ))
        fig.add_trace(go.Bar(
            x=names, y=zones, name='Zones',
            marker_color=COLORS[2], text=zones, textposition='outside', textfont=dict(size=10),
        ))
        fig.update_layout(**_theme_layout('Sectors & Zones per Farm', height=300), barmode='group')
        fig.update_yaxes(showgrid=True, gridcolor='#eee')
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
    except Exception:
        return None


def build_trees_per_farm_chart(farm_data):
    try:
        names = [d['name'] for d in farm_data if d['trees'] > 0]
        counts = [d['trees'] for d in farm_data if d['trees'] > 0]
        if not names:
            return None
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=names,
            y=counts,
            marker_color=COLORS[3],
            text=counts,
            textposition='outside',
            textfont=dict(size=11),
        ))
        fig.update_layout(**_theme_layout('Trees per Farm', height=280))
        fig.update_yaxes(showgrid=True, gridcolor='#eee')
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
    except Exception:
        return None
