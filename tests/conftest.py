import sys
import os
import threading
import time
import pytest
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))

BASE_URL = 'http://localhost:5001'
ADMIN_USER = 'admin'
ADMIN_PASS = 'admin123'


@pytest.fixture(scope='session')
def flask_app_and_db():
    os.environ['FLASK_ENV'] = 'development'
    os.environ['LOG_MODE'] = 'console'

    from app import create_app
    from app.database import init_db, get_db

    app = create_app()
    with app.app_context():
        init_db()
        db = get_db()
        yield app, db

    os._exit(0)


@pytest.fixture(scope='session')
def flask_app(flask_app_and_db):
    app, _ = flask_app_and_db
    return app


@pytest.fixture(scope='session')
def mongo_db(flask_app_and_db):
    _, db = flask_app_and_db
    return db


@pytest.fixture(scope='session')
def _start_server(flask_app):
    t = threading.Thread(
        target=lambda: flask_app.run(port=5001, debug=False, use_reloader=False),
        daemon=True
    )
    t.start()
    time.sleep(3)
    return t


@pytest.fixture(scope='session')
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser, _start_server):
    context = browser.new_context(viewport={'width': 1280, 'height': 720})
    page = context.new_page()
    page.goto(f'{BASE_URL}/auth/login', wait_until='networkidle')
    page.fill('input[name="username"]', ADMIN_USER)
    page.fill('input[name="password"]', ADMIN_PASS)
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')
    yield page
    context.close()


@pytest.fixture
def log(request):
    from helpers import TestLogger
    logger = TestLogger(request.node.name)
    yield logger
    passed = not hasattr(request.node, 'rep_call') or not request.node.rep_call.failed
    logger.done('PASSED' if passed else 'FAILED')


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    setattr(item, f"rep_{call.when}", outcome.get_result())
