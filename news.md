# SmartFarmerFlow - Release Notes

## [0.9.14] - 2026-09-06

### Added
- Automated version bump for commit


## v1.0.1 - 2026-09-06

### Bug Fix: Farm Delete Operation

**Problem**: Users reported that deleting farms was not working. The POST request to `/farms/<farm_id>/delete` returned a 302 redirect but the farm was not being removed from the database.

**Root Cause**: The `FarmModel._id` field is typed as `Optional[str]`, which caused some farms to be stored with string `_id` values in MongoDB. However, all delete (and other) queries used `ObjectId(farm_id)`, which never matched string `_id` values.

**Solution**: 
- Added `find_doc(collection, doc_id)` helper in `database.py` that tries ObjectId first, then falls back to string `_id`
- Updated all 6 blueprints (farms, sectors, zones, rows, trees, visits) to use this helper
- Fixed `FarmModel.check_duplicate()` to handle both ID types
- Added detailed logging for delete operations

**Files Changed**:
- `app/database.py` - Added `find_doc()` helper
- `app/blueprints/farms.py` - Updated all farm lookups
- `app/blueprints/sectors.py` - Updated sector farm lookups
- `app/blueprints/zones.py` - Updated zone farm lookups
- `app/blueprints/rows.py` - Updated row farm lookups
- `app/blueprints/trees.py` - Updated tree farm lookups
- `app/blueprints/visits.py` - Updated visit farm lookups
- `app/models/validation.py` - Fixed `check_duplicate()` method

---

## v1.0.0 - 2026-05-19

### Major Release

This release marks the first stable version of SmartFarmerFlow with comprehensive features for agricultural land management.

**Key Features**:
- Complete hierarchy management: Lands → Farms → Sectors → Zones → Rows → Trees
- Pydantic v2 validation for all data models
- Interactive Plotly maps with satellite view
- Bulk operations for all entity types
- Multi-language support (English, Arabic, French)
- Role-based access control (admin, worker, guest)
- Activity logging and audit trail
- Photo upload support for lands and farms

**Technical Improvements**:
- Refactored blueprints for better maintainability
- Enhanced calculation utilities with pyproj/shapely geodesic calculations
- Improved logging infrastructure with rotation
- Comprehensive test suite

---

## v0.9.1 - 2026-05-13

### Features & Improvements

- Auth decorators for centralized access control
- Geo calculations with pyproj/shapely
- Map browsing module with Leaflet.js
- Farm CRUD with legal docs and photo upload
- 500 error page with graceful handling
- LOG_MODE environment variable
- Farm translations in EN/AR/FR

---

## v0.8.0 - 2026-05-09

### Farm & Visit Management

- Added FarmModel and farms blueprint
- Added VisitModel and visits blueprint
- Farms now part of hierarchy: Lands → Farms → Sectors → Zones → Rows → Trees
- Coordinate calculation support for farms

---

## v0.7.0 - 2026-05-04

### UI Enhancements

- Bootstrap Tabs in Add Land modal
- Photo upload support
- Theme toggle buttons
- ZERO state pages
- Language buttons in btn-group

---

## v0.5.0 - 2026-05-03

### Pydantic Integration

- All blueprints refactored to use Pydantic models
- Bulk add functionality for all hierarchy levels
- Updated forms to match validation.py structure

---

## v0.4.0 - 2026-05-02

### CRUD Operations

- Full CRUD for all hierarchy levels
- Dedicated detail pages
- Delete with confirmation
- Admin-only access control
