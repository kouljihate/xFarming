import time
from datetime import datetime

BASE = 'http://localhost:5001'


def test_farm_crud(page, mongo_db, log):
    uid = str(int(time.time() * 1000))[-6:]
    farm_name = f"Farm {uid}"
    log.step(f"Starting farm CRUD test with name: {farm_name}")

    # ── Create a dedicated land for this test ──
    land = {
        'name': f"Auto Land {uid}",
        'location': {
            'address': {'street': '', 'city': '', 'state': '', 'postal_code': '', 'country': ''},
            'city': '',
            'center_coordinate': {'latitude': 0.0, 'longitude': 0.0},
            'altitude': {'minimum': 0.0, 'maximum': 0.0},
        },
        'metadata': {
            'established_date': datetime.now().strftime('%Y-%m-%d'),
            'last_updated': '', 'status': 'active', 'notes': '', 'version': 1
        },
        'farms': [],
        'created_at': datetime.now(),
    }
    result = mongo_db.lands.insert_one(land)
    land['_id'] = result.inserted_id
    land_id = str(land['_id'])
    log.info(f"Created land via DB for farm test: {land['name']} ({land_id})")

    try:
        # ── CREATE ──
        log.step("Navigate to Farms page")
        page.goto(f'{BASE}/farms/')
        page.wait_for_load_state('load')

        log.step("Open Add Farm modal")
        page.click('button[data-bs-target="#addFarmModal"]')
        page.wait_for_timeout(500)

        log.step("Fill create form")
        page.select_option('#addFarmModal select[name="land_id"]', land_id)
        page.fill('#addFarmModal input[name="farm_name"]', farm_name)
        page.fill('#addFarmModal textarea[name="description"]', 'Created by Playwright test')

        log.step("Submit create form")
        page.click('#addFarmModal button[name="action"][value="save"]')
        page.wait_for_timeout(3000)
        log.info(f"Current URL after create: {page.url}")

        log.step("Navigate to Farms page to verify")
        page.goto(f'{BASE}/farms/')
        page.wait_for_load_state('load')

        log.step("Verify farm appears in table")
        n = page.locator('table').filter(has_text=farm_name).count()
        assert n >= 1, f"Farm '{farm_name}' not found in table"
        log.info(f"Table entries: {n}")

        log.step("Verify farm in MongoDB")
        land2 = mongo_db.lands.find_one({'_id': land['_id']})
        assert land2 is not None, "Land not found after farm create"
        farm = None
        for f in land2.get('farms', []):
            if f.get('farm_name') == farm_name:
                farm = f
                break
        assert farm is not None, "Farm not found in land.farms after create"
        assert farm.get('description') == 'Created by Playwright test', "Description mismatch in DB"
        log.info(f"MongoDB farm _id: {farm['_id']}")
        log.info("MongoDB verification passed")

        fid = farm['_id']

        # ── EDIT ──
        new_name = f"{farm_name} E"
        log.step("Navigate to Farms page for edit")
        page.goto(f'{BASE}/farms/')
        page.wait_for_load_state('load')

        log.step("Open Edit Farm modal")
        page.click(f'button[data-bs-target="#editFarmModal{fid}"]')
        page.wait_for_timeout(500)

        log.step(f"Change name to: {new_name}")
        page.fill(f'#editFarmModal{fid} input[name="farm_name"]', new_name)

        log.step("Submit edit form")
        page.click(f'#editFarmModal{fid} button[name="action"][value="save"]')
        page.wait_for_timeout(3000)

        log.step("Verify edited farm in table")
        n2 = page.locator('table').filter(has_text=new_name).count()
        assert n2 >= 1, f"Edited farm '{new_name}' not in table"
        log.info(f"Table entries: {n2}")

        log.step("Verify edit in MongoDB")
        land3 = mongo_db.lands.find_one({'_id': land['_id']})
        farm2 = None
        for f in land3.get('farms', []):
            if f.get('_id') == fid:
                farm2 = f
                break
        assert farm2 is not None, "Farm not found in DB after edit"
        assert farm2['farm_name'] == new_name, f"Name mismatch in DB: '{farm2['farm_name']}' != '{new_name}'"
        log.info("MongoDB edit verification passed")

        log.step("Farm CRUD test completed successfully")
    finally:
        mongo_db.lands.delete_one({'_id': land['_id']})
        log.info(f"Cleaned up land {land_id}")
