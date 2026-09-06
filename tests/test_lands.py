import time

BASE = 'http://localhost:5001'


def test_land_crud(page, mongo_db, log):
    uid = str(int(time.time() * 1000))[-6:]
    land_name = f"Test {uid}"
    land_id = None
    log.step(f"Starting land CRUD test with name: {land_name}")

    try:
        # ── CREATE ──
        log.step("Navigate to Lands page")
        page.goto(f'{BASE}/lands/')
        page.wait_for_load_state('load')

        log.step("Open Add Land modal")
        page.click('button[data-bs-target="#addLandModal"]')
        page.wait_for_timeout(500)

        log.step("Fill create form")
        page.fill('input[name="name"]', land_name)
        page.fill('input[name="latitude"]', '31.12')
        page.fill('input[name="longitude"]', '-7.56')
        page.fill('input[name="established_date"]', '2024-01-15')
        page.select_option('select[name="status"]', 'active')
        page.fill('textarea[name="notes"]', 'Created by Playwright test')

        log.step("Submit create form")
        page.click('button[type="submit"]:has-text("Save Land")')
        page.wait_for_timeout(3000)
        log.info(f"Current URL after create: {page.url}")

        log.step("Verify land appears in table")
        n = page.locator('table').filter(has_text=land_name).count()
        assert n >= 1, f"Land '{land_name}' not found in table"
        log.info(f"Table entries: {n}")

        log.step("Verify land in MongoDB")
        land = mongo_db.lands.find_one({'name': land_name})
        assert land is not None, "Land not saved in MongoDB after create"
        land_id = land['_id']
        log.info(f"MongoDB _id: {land_id}")
        assert land.get('metadata', {}).get('status') == 'active', "Status mismatch in DB"
        assert land.get('metadata', {}).get('notes') == 'Created by Playwright test', "Notes mismatch in DB"
        log.info("MongoDB verification passed")

        lid = str(land_id)

        # ── EDIT ──
        new_name = f"{land_name} E"
        log.step(f"Navigate to Lands page for edit")
        page.goto(f'{BASE}/lands/')
        page.wait_for_load_state('load')

        log.step("Open Edit Land modal")
        page.click(f'button[data-bs-target="#editLandModal{lid}"]')
        page.wait_for_timeout(500)

        log.step(f"Change name to: {new_name}")
        page.fill(f'#editLandModal{lid} input[name="name"]', new_name)

        log.step("Submit edit form")
        page.click(f'#editLandModal{lid} button:has-text("Update")')
        page.wait_for_timeout(3000)

        log.step("Verify edited land in table")
        n2 = page.locator('table').filter(has_text=new_name).count()
        assert n2 >= 1, f"Edited land '{new_name}' not in table"
        log.info(f"Table entries: {n2}")

        log.step("Verify edit in MongoDB")
        land2 = mongo_db.lands.find_one({'_id': land_id})
        assert land2 is not None, "Land not found in MongoDB after edit"
        assert land2['name'] == new_name, f"Name mismatch in DB: '{land2['name']}' != '{new_name}'"
        log.info("MongoDB edit verification passed")

        log.step("Land CRUD test completed successfully")
    finally:
        if land_id:
            mongo_db.lands.delete_one({'_id': land_id})
            log.info(f"Cleaned up land {land_id}")
