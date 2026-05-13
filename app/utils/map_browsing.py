import os
import webbrowser


def generate_map(
    coords: list[tuple[float, float]],
    label: str = "Parcel",
    output_path: str = "map.html",
    open_browser: bool = True,
) -> str:
    """
    Generate a standalone HTML file showing the polygon traced on an
    interactive map (Leaflet.js — no API key required).

    Args:
        coords       : List of (latitude, longitude) tuples.
        label        : Display name shown on the map.
        output_path  : Where to write the HTML file.
        open_browser : Automatically open the map in the default browser.

    Returns:
        Absolute path to the generated HTML file.
    """
    # centroid = calculate_centroid(coords)
    c_lat    = coords["latitude"]
    c_lon    = coords["longitude"]
    gmaps    = coords["maps_url"]
    n_verts  = len(coords)

    # Close the ring for display if needed
    closed = list(coords)
    if closed[0] != closed[-1]:
        closed.append(closed[0])

    js_coords = ",\n            ".join(
        f"[{lat}, {lon}]" for lat, lon in closed
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{label} — Polygon Map</title>
  <link rel="stylesheet"
        href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    *, *::before, *::after {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{
      font-family: 'Segoe UI', sans-serif;
      background: #0b0c0f;
      color: #d4d8e8;
      height: 100vh;
      display: flex;
      flex-direction: column;
    }}
    header {{
      background: #13151a;
      border-bottom: 3px solid #e8ff47;
      padding: .7rem 1.4rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: .5rem;
      z-index: 1000;
      position: relative;
    }}
    header::after {{
      content: "LEAFLET + OSM";
      position: absolute;
      top: 0; right: 1.2rem;
      font-family: monospace;
      font-size: .58rem;
      color: #0b0c0f;
      background: #e8ff47;
      padding: 1px 7px;
      letter-spacing: .1em;
    }}
    header h1 {{
      font-family: 'Courier New', monospace;
      font-size: 1rem;
      color: #e8ff47;
      letter-spacing: .1em;
    }}
    .meta {{
      font-family: 'Courier New', monospace;
      font-size: .68rem;
      color: #6b7394;
    }}
    #map {{ flex: 1; width: 100%; }}
    .info-bar {{
      background: #13151a;
      border-top: 1px solid #2a2d36;
      padding: .55rem 1.4rem;
      display: flex;
      gap: 2rem;
      flex-wrap: wrap;
      font-family: 'Courier New', monospace;
      font-size: .7rem;
    }}
    .info-bar .item span {{ color: #6b7394; margin-right: .35rem; }}
    .info-bar .item strong {{ color: #e8ff47; }}
    .info-bar a {{ color: #e8ff47; text-decoration: none; }}
    /* Leaflet dark overrides */
    .leaflet-container {{ background: #1a1c23; }}
    .leaflet-popup-content-wrapper {{
      background: #13151a; color: #d4d8e8;
      border: 1px solid #2a2d36; border-radius: 2px;
      font-family: 'Courier New', monospace; font-size: .78rem;
    }}
    .leaflet-popup-tip {{ background: #13151a; }}
    .leaflet-popup-content {{ margin: 10px 14px; line-height: 1.6; }}
    .leaflet-control-zoom a {{
      background: #13151a !important; color: #e8ff47 !important;
      border-color: #2a2d36 !important;
    }}
    .leaflet-control-attribution {{
      background: rgba(19,21,26,.85) !important;
      color: #4a4f61 !important; font-size: .58rem;
    }}
    .leaflet-control-attribution a {{ color: #6b7394 !important; }}
  </style>
</head>
<body>

<header>
  <h1>&#9670; {label.upper()}</h1>
  <div class="meta">centroid &rarr; {c_lat}, {c_lon} &nbsp;|&nbsp; {n_verts} vertices</div>
</header>

<div id="map"></div>

<div class="info-bar">
  <div class="item"><span>CENTROID LAT</span><strong>{c_lat}</strong></div>
  <div class="item"><span>CENTROID LON</span><strong>{c_lon}</strong></div>
  <div class="item"><span>VERTICES</span><strong>{n_verts}</strong></div>
  <div class="item"><span>GMAPS</span><strong><a href="{gmaps}" target="_blank">Open &nearr;</a></strong></div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
  // ── MAP ────────────────────────────────────────────────────
  const map = L.map('map').setView([{c_lat}, {c_lon}], 17);

  L.tileLayer(
    'https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png',
    {{ attribution: '&copy; OpenStreetMap &amp; CartoDB', subdomains:'abcd', maxZoom:21 }}
  ).addTo(map);

  // ── POLYGON ─────────────────────────────────────────────────
  const poly = L.polygon([
    {js_coords}
  ], {{
    color:       '#e8ff47',
    weight:      2.5,
    opacity:     1,
    fillColor:   '#e8ff47',
    fillOpacity: 0.10,
    dashArray:   null,
  }}).addTo(map);

  poly.bindPopup(
    '<b style="color:#e8ff47">{label}</b><br/>' +
    'Vertices: {n_verts}'
  );

  // ── CENTROID ────────────────────────────────────────────────
  const dot = L.divIcon({{
    className: '',
    html: '<div style="width:14px;height:14px;background:#e8ff47;border:2px solid #0b0c0f;border-radius:50%;box-shadow:0 0 10px #e8ff4799;"></div>',
    iconSize: [14,14], iconAnchor: [7,7],
  }});

  L.marker([{c_lat}, {c_lon}], {{ icon: dot }})
    .addTo(map)
    .bindPopup(
      '<b style="color:#e8ff47">Centroid</b><br/>' +
      'Lat: {c_lat}<br/>Lon: {c_lon}'
    )
    .openPopup();

  // ── FIT TO POLYGON ──────────────────────────────────────────
  map.fitBounds(poly.getBounds(), {{ padding: [40, 40] }});
</script>
</body>
</html>"""

    abs_path = os.path.abspath(output_path)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  Map saved  → {abs_path}")

    if open_browser:
        webbrowser.open(f"file://{abs_path}")

    return abs_path

