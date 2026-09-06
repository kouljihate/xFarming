import time
from datetime import datetime
from bson import ObjectId
from data_generator import _uid, land_data, farm_data, sector_data

BASE = 'http://localhost:5001'


def _find_sector_in_land(land, sector_name):
    for farm in land.get('farms', []):
        for sector in farm.get('sectors', []):
            if sector.get('name') == sector_name:
                return sector, farm
    return None, None


def test_sector_crud(page, mongo_db, log):
    uid = _uid()
    sector_name = f"Test Sector {uid}"
    log.step(f"Starting sector CRUD test with name: {sector_name}")

    # ── Seed Land + Farm in DB ──
    log.step("Seed prerequisite Land and Farm in DB")

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
    log.info(f"Created farm: {farm_name} ({farm_id})")

    land = mongo_db.lands.find_one({'_id': land_id})
    assert land is not None, "Seed land not found"
    assert len(land.get('farms', [])) == 1, "Seed farm not in land"

    try:
        # ── CREATE ──
        log.step("Navigate to Sectors page")
        page.goto(f'{BASE}/sectors/')
        page.wait_for_load_state('load')

        log.step("Open Add Sector modal")
        page.click('button[data-bs-target="#addSectorModal"]')
        page.wait_for_timeout(500)

        log.step("Select land in modal")
        page.select_option('#addSectorModal select[name="land_id"]', str(land_id))
        page.wait_for_timeout(500)

        log.step("Select farm in modal")
        page.select_option('#addSectorModal select[name="farm_id"]', farm_id)
        page.wait_for_timeout(300)

        log.step("Fill create form")
        page.fill('#addSectorModal input[name="name"]', sector_name)
        page.fill('#addSectorModal input[name="sector_number"]', '1')
        page.fill('#addSectorModal input[name="area"]', '25.5')
        page.select_option('#addSectorModal select[name="soil_type"]', 'loam')
        page.fill('#addSectorModal input[name="irrigation_type"]', 'drip')
        page.fill('#addSectorModal textarea[name="notes"]', f'Created by test {uid}')

        log.step("Submit create form")
        page.click('#addSectorModal button[type="submit"]')
        page.wait_for_timeout(3000)
        log.info(f"Current URL after create: {page.url}")

        log.step("Verify sector appears in table")
        n = page.locator('table').filter(has_text=sector_name).count()
        assert n >= 1, f"Sector '{sector_name}' not found in table"
        log.info(f"Table entries: {n}")

        log.step("Verify sector in MongoDB")
        land_after = mongo_db.lands.find_one({'_id': land_id})
        assert land_after is not None, "Land not found after sector create"
        sector, parent_farm = _find_sector_in_land(land_after, sector_name)
        assert sector is not None, "Sector not found in land.farms[].sectors[] after create"
        assert sector.get('name') == sector_name, "Name mismatch in DB"
        assert sector.get('description', '') == '', "Description should be empty"
        assert sector.get('location', {}).get('area', {}).get('value') == 25.5, "Area mismatch in DB"
        assert sector.get('location', {}).get('soil_type') == 'loam', "Soil type mismatch in DB"
        assert sector.get('location', {}).get('irrigation_type') == 'drip', "Irrigation type mismatch in DB"
        assert sector.get('metadata', {}).get('notes') == f'Created by test {uid}', "Notes mismatch in DB"
        log.info(f"MongoDB sector _id: {sector['_id']}")
        log.info("MongoDB creation verification passed")

        sector_id = sector['_id']

        # ── EDIT ──
        new_name = f"{sector_name} E"
        log.step("Navigate to Sectors page for edit")
        page.goto(f'{BASE}/sectors/')
        page.wait_for_load_state('load')

        log.step("Open Edit Sector modal")
        page.click(f'button[data-bs-target="#editSectorModal{sector_id}"]')
        page.wait_for_timeout(500)

        log.step(f"Change name to: {new_name}")
        page.fill(f'#editSectorModal{sector_id} input[name="name"]', new_name)

        log.step("Submit edit form")
        page.click(f'#editSectorModal{sector_id} button[type="submit"]')
        page.wait_for_timeout(3000)

        log.step("Verify edited sector in table")
        n2 = page.locator('table').filter(has_text=new_name).count()
        assert n2 >= 1, f"Edited sector '{new_name}' not in table"
        log.info(f"Table entries: {n2}")

        log.step("Verify edit in MongoDB")
        land_after_edit = mongo_db.lands.find_one({'_id': land_id})
        sector2, _ = _find_sector_in_land(land_after_edit, new_name)
        assert sector2 is not None, "Sector not found in DB after edit"
        assert sector2['name'] == new_name, f"Name mismatch in DB: '{sector2['name']}' != '{new_name}'"
        log.info("MongoDB edit verification passed")

        log.step("Sector CRUD test completed successfully")
    finally:
        mongo_db.lands.delete_one({'_id': land_id})
        log.info(f"Cleaned up land {land_id}")
