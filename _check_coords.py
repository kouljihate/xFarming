from app import create_app
from app.database import get_db
app = create_app()
with app.app_context():
    db = get_db()
    lands = list(db.lands.find())
    for land in lands:
        loc = land.get('location', {})
        cc = loc.get('center_coordinate', {})
        oc = loc.get('coordinates', {})
        print(f"{land.get('name', '?')}:  center_coord=({cc.get('latitude')}, {cc.get('longitude')})  |  old_coords=({oc.get('latitude')}, {oc.get('longitude')})")
    print(f"Total lands: {len(lands)}")
