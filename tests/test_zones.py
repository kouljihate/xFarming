import time
from datetime import datetime
from bson import ObjectId
from data_generator import _uid, land_data, farm_data, sector_data, zone_data

BASE = 'http://localhost:5001'


def _find_zone_in_land(land, zone_name):
    for farm in land.get('farms', []):
        for sector in farm.get('sectors', []):
            for zone in sector.get('zones', []):
                if zone.get('name') == zone_name:
                    return zone, sector, farm
    return None, None, None


def test_zone_crud(page, mongo_db, log):
    uid = _uid()
    zone_name = f"Test Zone {uid}"
    log.step(f"Starting zone CRUD test with name: {zone_name}")

    # ── Seed Land + Farm + Sector in DB ──
    log.step("Seed prerequisite Land, Farm and Sector in DB")

    ld = land_data(uid)
    land_result = mongo_db.lands.insert_one(ld)
    land_id = land_result.inserted_id
    log.info(f"Created land: {ld['name']} ({land_id})")

    fd = farm_data(uid)
    farm_id = fd['_id']
    farm_name = fd['farm_name']
    mongo_db.lands.update_one(
        {'_id': land_id},
        {'$push': {'farms': fd}, '$set': {'last_updated_at': datetime.now().isoformat()}}
    )

    sd = sector_data(uid)
    sector_id = sd['_id']
    sector_name = sd['name']
    mongo_db.lands.update_one(
        {'_id': land_id, 'farms._id': farm_id},
        {'$push': {'farms.$.sectors': sd}, '$set': {'last_updated_at': datetime.now().isoformat()}}
    )
    log.info(f"Created sector: {sector_name} ({sector_id})")

    land = mongo_db.lands.find_one({'_id': land_id})
    assert land is not None, "Seed land not found"
    assert len(land.get('farms', [])) == 1, "Seed farm not in land"
    assert len(land['farms'][0].get('sectors', [])) == 1, "Seed sector not in farm"

    try:
        # ── CREATE via direct API ──
        log.step("Navigate to Sectors page to get CSRF / session")
        page.goto(f'{BASE}/sectors/')
        page.wait_for_load_state('load')

        log.step("Submit zone creation via POST API")
        response = page.request.post(f'{BASE}/zones/add', form={
            'land_id': str(land_id),
            'sector_id': sector_id,
            'name': zone_name,
            'description': f'Description for zone {uid}',
            'area_value': '5.0',
            'area_unit': 'ha',
            'row_spacing_value': '12',
            'row_spacing_unit': 'feet',
            'tree_spacing_value': '15',
            'tree_spacing_unit': 'feet',
            'orientation': 'N-S',
            'current_crop': 'Olives',
            'variety': 'Arbequina',
            'planting_date': '2024-03-01',
            'root_stock': 'Olea-europaea',
            'pollinators': 'Coratina, Leccino',
            'soil_type': 'clay_loam',
            'ph': '7.2',
            'organic_matter': '2.5%',
            'drainage': 'well-drained',
            'total_rows': '20',
            'total_trees': '400',
            'trees_per_acre': '80',
            'active_trees': '390',
            'dead_trees': '10',
            'replacement_rate': '2.5%',
            'last_pruned': '2024-06-01',
            'last_fertilized': '2024-04-15',
            'last_irrigated': '2024-07-01',
            'next_maintenance': '2024-09-01',
            'maintenance_notes': 'Regular schedule',
            'created_date': '2024-01-20',
            'status': 'active',
            'zone_manager': 'Test Manager',
            'notes': f'Created by test {uid}',
        })
        log.info(f"POST response status: {response.status}, url: {response.url}")

        # ── Verify in MongoDB ──
        log.step("Verify zone in MongoDB")
        land_after = mongo_db.lands.find_one({'_id': land_id})
        assert land_after is not None, "Land not found after zone create"
        zone, parent_sector, parent_farm = _find_zone_in_land(land_after, zone_name)
        assert zone is not None, "Zone not found in land.farms[].sectors[].zones[] after create"

        assert zone['name'] == zone_name, "Name mismatch in DB"
        assert zone['description'] == f'Description for zone {uid}', "Description mismatch in DB"
        assert zone['location']['area']['value'] == 5.0, "Area mismatch in DB"
        assert zone['location']['row_spacing']['value'] == 12, "Row spacing mismatch"
        assert zone['location']['tree_spacing']['value'] == 15, "Tree spacing mismatch"
        assert zone['location']['orientation'] == 'N-S', "Orientation mismatch"
        assert zone['crop_info']['current_crop'] == 'Olives', "Crop mismatch"
        assert zone['crop_info']['variety'] == 'Arbequina', "Variety mismatch"
        assert zone['crop_info']['planting_date'] == '2024-03-01', "Planting date mismatch"
        assert 'Coratina' in zone['crop_info'].get('pollinators', []), "Pollinators missing"
        assert zone['soil_characteristics']['type'] == 'clay_loam', "Soil type mismatch"
        assert zone['soil_characteristics']['ph'] == 7.2, "pH mismatch"
        assert zone['statistics']['total_rows'] == 20, "Total rows mismatch"
        assert zone['statistics']['total_trees'] == 400, "Total trees mismatch"
        assert zone['metadata']['status'] == 'active', "Status mismatch"
        assert zone['metadata']['notes'] == f'Created by test {uid}', "Notes mismatch"
        assert zone['metadata']['zone_manager'] == 'Test Manager', "Zone manager mismatch"
        log.info(f"MongoDB zone _id: {zone['_id']}")
        log.ok("MongoDB creation verification passed")

        zone_id = zone['_id']

        # ── Verify in UI table ──
        log.step("Navigate to Zones page to verify table")
        page.goto(f'{BASE}/zones/')
        page.wait_for_load_state('load')

        log.step("Verify zone appears in table")
        n = page.locator('table').filter(has_text=zone_name).count()
        assert n >= 1, f"Zone '{zone_name}' not found in table"
        log.info(f"Table entries: {n}")

        # ── EDIT ──
        new_name = f"{zone_name} E"
        log.step("Navigate to Zones page for edit")
        page.goto(f'{BASE}/zones/')
        page.wait_for_load_state('load')

        log.step("Open Edit Zone modal")
        page.click(f'button[data-bs-target="#editZoneModal{zone_id}"]')
        page.wait_for_timeout(500)

        log.step(f"Change name to: {new_name}")
        page.fill(f'#editZoneModal{zone_id} input[name="name"]', new_name)

        log.step("Change status to inactive")
        page.select_option(f'#editZoneModal{zone_id} select[name="status"]', 'inactive')

        log.step("Submit edit form")
        page.click(f'#editZoneModal{zone_id} button[type="submit"]')
        page.wait_for_timeout(3000)

        log.step("Verify edited zone in table")
        n2 = page.locator('table').filter(has_text=new_name).count()
        assert n2 >= 1, f"Edited zone '{new_name}' not in table"
        log.info(f"Table entries: {n2}")

        log.step("Verify edit in MongoDB")
        land_after_edit = mongo_db.lands.find_one({'_id': land_id})
        zone2, _, _ = _find_zone_in_land(land_after_edit, new_name)
        assert zone2 is not None, "Zone not found in DB after edit"
        assert zone2['name'] == new_name, f"Name mismatch in DB: '{zone2['name']}' != '{new_name}'"
        assert zone2['metadata']['status'] == 'inactive', f"Status not updated in DB: '{zone2.get('metadata', {}).get('status')}'"
        log.ok("MongoDB edit verification passed")

        log.step("Zone CRUD test completed successfully")
    finally:
        mongo_db.lands.delete_one({'_id': land_id})
        log.info(f"Cleaned up land {land_id}")
