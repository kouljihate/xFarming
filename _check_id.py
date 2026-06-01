from pymongo import MongoClient
from dotenv import load_dotenv
import os
load_dotenv()
client = MongoClient(os.getenv('MONGO_URI'))
db = client['xfarming']
land = db.lands.find_one({'farms': {'$exists': True, '$ne': []}}, {'farms.$': 1})
if land:
    farm = land['farms'][0]
    print('_id type:', type(farm.get('_id')))
    print('_id value:', repr(farm.get('_id')))
    print('All keys:', list(farm.keys()))
else:
    print('No lands with farms')
