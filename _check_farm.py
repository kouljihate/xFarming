import sys
try:
    from pymongo import MongoClient
    import os
    from dotenv import load_dotenv

    load_dotenv()
    uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/xfarming')
    print("URI:", uri)
    client = MongoClient(uri)

    # Use the database from the URI path
    from urllib.parse import urlparse
    parsed = urlparse(uri)
    db_name = parsed.path.lstrip('/') if parsed.path else 'xfarming'
    print("DB name:", db_name)
    db = client[db_name]
    col_names = db.list_collection_names()
    print("Collections:", col_names)
    lands = list(db.lands.find())
    print("Total lands:", len(lands))
    for land in lands:
        farms = land.get('farms', [])
        print("Land '{}' has {} farms".format(land.get('name'), len(farms)))
        for farm in farms:
            keys = list(farm.keys())
            print("  Farm keys:", keys)
            loc = farm.get('location', {})
            print("    location keys: {}".format(list(loc.keys())))
            print("    soil_type: {}".format(loc.get('soil_type', 'MISSING')))
            irrig = farm.get('irrigation_system', {})
            print("    irrigation_system: {}".format(irrig if irrig else 'MISSING'))
            legal = farm.get('legal', {})
            print("    legal: {}".format(legal if legal else 'MISSING'))
            meta = farm.get('metadata', {})
            print("    metadata: {}".format(meta if meta else 'MISSING'))
except Exception as e:
    print("ERROR:", e)
    import traceback
    traceback.print_exc()
