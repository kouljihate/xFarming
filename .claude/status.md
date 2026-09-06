# Status

## Goal
Fix bugs (farm view, area calculation) and add version display + error handling across the project.

## Constraints & Preferences
- Flask + MongoDB, server-rendered, no JS logic
- Git tag workflow: pre-commit hook auto-bumps version
- All functions must have try/except returning error info (message, function, line)
- Blueprint route errors must flash message and redirect (not return dicts)
- Utility function errors return `{'error': True, 'message': ..., 'function': ..., 'line': ..., 'trace': ...}`

## Progress
### Done
- Version v0.9.3 tagged and pushed to `https://github.com/kouljihate/xFarming.git`
- Added `v{{ app_version }}` at bottom of sidebar in `base.html`
- Fixed Farm View button (missing `_id` in add route, ObjectId vs string comparison in detail/edit/delete)
- Ran migration script to add `_id` to existing farm in xfarming MongoDB database
- Changed Farm/Detail page to use the same Edit/Delete modals as Farm/Index
- Fixed area calculation: duplicate `"area_ha"` key overwrote hectares with acres; renamed second to `"area_acres"`
- Added try/except blocks with `_error_info()` helper to ALL functions in:
  - `app/utils/calculation.py` (8 functions)
  - `app/utils/map_utils.py` (2 functions)
  - `app/utils/map_browsing.py` (1 function)
  - `app/database.py` (2 functions)
  - `app/utils/logging.py` (all functions, decorators)
  - `app/translations.py` (t function)
  - `app/__init__.py` (create_app, error handlers, index route)
  - `app/blueprints/auth.py`, `dashboard.py`, `activities.py`, `users.py`
  - `app/blueprints/trees.py`, `rows.py`, `zones.py`
  - `app/blueprints/lands.py`, `farms.py`, `sectors.py`, `visits.py`
- Fixed `farm['name']` → `farm.get('farm_name', '')` KeyError in farms.py, trees.py, rows.py, zones.py
- Fixed missing `land_id` variable bug in rows.py add route
- Fixed `tree['name']` → `tree.get('name', '')` in trees.py

### In Progress
- None

## Key Decisions
- Error format for blueprint routes: log + flash + redirect (cannot return dicts)
- Error format for utility functions: dict with `error`, `message`, `function`, `line`, `trace`
- Pydantic models (`validation.py`) left unchanged since they have built-in validation
- Pre-commit hook auto-bumps version; tag after commit to match bumped value

## Next Steps
1. Verify all modified files compile with `py_compile` ✓
2. Restart Flask server for changes to take effect

## Critical Context
- MongoDB database: `xfarming` on `mongodb://localhost:27017/xfarming`
- The pre-commit hook auto-increments VERSION and `__init__.py` `__version__` on every commit
- `area_ha` bug was a duplicate dict key — Python kept the second (acres) instead of hectares
- Farm `_id` issue: existing DB farms had no `_id` at all → `url_for` generated `/farms/` (same as index)

## Relevant Files
- `app/utils/calculation.py`: 8 functions, try/except + `_error_info()` helper, fixed duplicate `area_ha`
- `app/blueprints/farms.py`: View button fix, string vs ObjectId comparisons, `farm_name` fallback
- `app/templates/farms/detail.html`: Added modal includes for edit/delete
- `app/templates/farms/index.html`: View button with `farm._id`
- `app/templates/base.html`: Sidebar shows `v{{ app_version }}` at bottom
- `app/__init__.py`: `__version__='0.9.3'`, `app_version` Jinja global
- `VERSION`: `0.9.3`
- `app/database.py`: `get_db()` and `init_db()` with try/except, error dict propagation
- `app/utils/logging.py`: All functions wrapped; `_get_caller_info` returns tuple on error
- `app/utils/map_utils.py`: `build_lands_map`, `build_land_detail_map` wrapped
- `app/utils/map_browsing.py`: `generate_map` wrapped
- `app/translations.py`: `t()` wrapped, returns key on error
- `.env`: `MONGO_URI=mongodb://localhost:27017/xfarming`
