import os
import sys
import subprocess
import glob
import json
import time
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pymongo import MongoClient

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

TEST_FILES = [
    ('test_lands.py', 'Lands'),
    ('test_farms.py', 'Farms'),
    ('test_sectors.py', 'Sectors'),
    ('test_zones.py', 'Zones'),
]

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/SmartFarmerFlow')

RESULTS_FILE = BASE_DIR / '.dashboard_results.json'


def load_results():
    if RESULTS_FILE.exists():
        try:
            with open(RESULTS_FILE) as f:
                return json.load(f)
        except:
            pass
    return {}


def save_result(name, passed, output):
    results = load_results()
    entry = {
        'name': name,
        'passed': passed,
        'output': output,
        'timestamp': datetime.now().isoformat(),
    }
    if name not in results:
        results[name] = []
    results[name].append(entry)
    results[name] = results[name][-20:]
    with open(RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    return entry


@st.cache_resource
def get_mongo():
    client = MongoClient(MONGO_URI)
    return client.get_database()


def run_pytest(test_file):
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', str(BASE_DIR / test_file), '-v', '--tb=short', '--no-header'],
        capture_output=True, text=True, timeout=120,
    )
    output = result.stdout + result.stderr
    passed = ' passed' in output.splitlines()[-1] if output.splitlines() else False
    return output, passed


st.set_page_config(page_title='SFarming Test Dashboard', layout='wide')
st.title('\U0001F331 SmartFarmerFlow — Test Dashboard')

# ── Sidebar ──
st.sidebar.header('Test Controls')

test_choice = st.sidebar.radio(
    'Select test',
    [label for _, label in TEST_FILES],
    index=0,
)

run_selected = st.sidebar.button(f'\U000025B6 Run {test_choice}', type='primary', use_container_width=True)
run_all = st.sidebar.button('\U000026A1 Run All Tests', use_container_width=True)
st.sidebar.divider()
refresh_db = st.sidebar.button('\U0001F504 Refresh DB Stats', use_container_width=True)

# ── DB Stats ──
st.sidebar.subheader('Database')
try:
    db = get_mongo()
    land_count = db.lands.count_documents({})
    farm_count = sum(len(land.get('farms', [])) for land in db.lands.find())
    st.sidebar.metric('Lands', land_count)
    st.sidebar.metric('Farms', farm_count)
except Exception as e:
    st.sidebar.error(f'DB: {e}')

# ── Main content: tabs ──
tab1, tab2, tab3 = st.tabs(['\U000025B6 Test Runner', '\U0001F4CA History', '\U0001F4DD Logs'])

with tab1:
    results = load_results()
    col1, col2, col3, col4 = st.columns(4)

    test_map = {label: fname for fname, label in TEST_FILES}
    selected_file = test_map[test_choice]

    for idx, (fname, label) in enumerate(TEST_FILES):
        col = [col1, col2, col3, col4][idx]
        history = results.get(label, [])
        last_run = history[-1] if history else None

        with col:
            st.subheader(label)
            if last_run:
                if last_run['passed']:
                    st.markdown(f'<h1 style="color:green;text-align:center;">\u2713</h1>', unsafe_allow_html=True)
                    st.caption(f'Passed at {last_run["timestamp"][:19]}')
                else:
                    st.markdown(f'<h1 style="color:red;text-align:center;">\u2717</h1>', unsafe_allow_html=True)
                    st.caption(f'Failed at {last_run["timestamp"][:19]}')
                runs = len(history)
                passes = sum(1 for r in history if r['passed'])
                st.caption(f'{passes}/{runs} passes ({runs} runs)')
            else:
                st.markdown(f'<h1 style="color:gray;text-align:center;">&mdash;</h1>', unsafe_allow_html=True)
                st.caption('Not run yet')

    st.divider()

    if run_selected:
        st.info(f'Running {selected_file}...')
        progress = st.progress(0, text='Starting...')
        output, passed = run_pytest(selected_file)
        progress.progress(100, text='Done' if passed else 'Failed')
        entry = save_result(test_choice, passed, output)

        if passed:
            st.success(f'\u2705 {test_choice} tests **PASSED**')
        else:
            st.error(f'\u274C {test_choice} tests **FAILED**')

        with st.expander('View test output', expanded=not passed):
            st.text(output)

        st.rerun()

    if run_all:
        st.info('Running all tests...')
        overall_pass = True
        output_container = st.empty()
        all_output = ''
        for fname, label in TEST_FILES:
            with st.spinner(f'Running {label}...'):
                output, passed = run_pytest(fname)
                save_result(label, passed, output)
                all_output += f'=== {label} ===\n{output}\n\n'
                if not passed:
                    overall_pass = False
        output_container.text(all_output)
        if overall_pass:
            st.success('\u2705 All tests passed!')
        else:
            st.error('\u274C Some tests failed!')
        st.rerun()

with tab2:
    st.header('Test History')
    results = load_results()
    if not results:
        st.info('No test runs yet.')
    else:
        rows = []
        for label, runs in results.items():
            for run in reversed(runs):
                rows.append({
                    'Test': label,
                    'Status': '\u2705 Pass' if run['passed'] else '\u274C Fail',
                    'Time': run['timestamp'][:19],
                    'Output (preview)': run['output'][:200] + '...' if len(run['output']) > 200 else run['output'],
                })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

with tab3:
    st.header('Test Log Files')
    log_files = sorted(
        glob.glob(str(LOG_DIR / '*.log')),
        key=os.path.getmtime, reverse=True
    )
    if not log_files:
        st.info('No log files found. Run a test first.')
    else:
        log_names = [Path(f).stem for f in log_files]
        selected_log = st.selectbox('Select log', log_names)
        log_path = LOG_DIR / f'{selected_log}.log'
        if log_path.exists():
            content = log_path.read_text(encoding='utf-8')
            st.text_area('Log content', content, height=500)
