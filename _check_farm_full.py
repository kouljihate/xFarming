from pymongo import MongoClient
from dotenv import load_dotenv
from bson import ObjectId
import os, json

load_dotenv()
client = MongoClient(os.getenv('MONGO_URI'))
db = client['xfarming']
land = db.lands.find_one({'farms': {'$exists': True, '$ne': []}})
if land:
    for farm in land['farms']:
        print("Full farm data:")
        for k, v in farm.items():
            print("  {}: {}".format(k, repr(v)[:100]))
else:
    print("No lands with farms")
