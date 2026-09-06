# SmartFarmerFlow - Version History

## [1.0.1] - 2026-09-06

### Fixed
- **Farm delete operation**: Resolved critical bug where farms with string `_id` in MongoDB could not be deleted due to ObjectId query mismatch
- **Universal document lookup**: Added `find_doc()` helper in `database.py` that handles both ObjectId and string `_id` formats
- **All blueprints updated**: farms, sectors, zones, rows, trees, visits blueprints now use `find_doc()` for consistent MongoDB queries
- **FarmModel.check_duplicate()**: Updated to handle both ObjectId and string exclude_id formats
- **Delete endpoint logging**: Added detailed logging for farm deletion attempts with success/failure feedback

### Changed
- Version bumped to 1.0.1

## [1.0.0] - 2026-05-19

### Added
- Version number display at bottom of sidebar
- Enhanced map utilities with new map_utils.py module
- Improved logging infrastructure with log rotation
- Additional data validation checks in utility scripts
- Enhanced farm and land management capabilities
- Comprehensive test suite for farms, lands, sectors, zones

### Changed
- Updated version references throughout the codebase
- Refactored blueprint implementations for better maintainability
- Improved template structures for farms and lands
- Enhanced validation models with stricter constraints
- Updated calculation utilities for better precision
- Improved translation management system
- Enhanced database connection handling

### Fixed
- Resolved various UI inconsistencies in modal dialogs
- Fixed form validation issues in farm and land modules
- Addressed template rendering problems
- Fixed coordinate calculation edge cases
- Resolved logging file handle issues

## [0.9.1] - 2026-05-13

### Added
- **Auth decorators**: `@login_required`, `@admin_required`, `@log_func_call` in `app/utils/logging.py` — centralized session/role checks
- **Geo calculations**: `calculate_centroid()` and `calculate_polygon_metrics()` using pyproj/shapely geodesic WGS84
- **Map browsing module**: `app/utils/map_browsing.py` — standalone Leaflet map generation with polygon visualization and centroid marker
- **500 error page** with graceful error handling and user-friendly message
- **Farms CRUD templates**: `app/templates/farms/{index,detail,edit}.html` + farm modals (Add with tabs, Edit, Delete)
- **Farm legal documents** and **photo upload** support in farm add/edit forms
- **Google Maps URL** generation from centroid coordinates, linked in farm detail
- **LOG_MODE env var**: console-only (`--debug-console`), file-only (`--debug-file`), or combined logging
- **Farm translations**: keys for `farms`, `total_farms`, `add_farm`, `farm`, `view` in English, Arabic, and French

### Changed
- **Lands blueprint refactored**: removed legacy sector management from lands; simplified LandModel location structure with `center_coordinate` and `altitude` fields
- **Farms blueprint refactored**: action-based form handling (`calculate`/`show_map`/submit); form data preserved on calculation errors; legal/photos fields integrated
- **Calculation module**: enhanced with pyproj/shapely geodesic calculations — returns `area_ha`, `perimeter_m`, centroid with `maps_url`
- **Logging system**: LOG_MODE controls console/file/combined output; `log_message` now also logs to Flask logger and stdout
- **Dashboard**: farm statistics integrated into dashboard counts
- **Translations**: added farm-related keys across all supported languages
- **Area unit**: changed default from `acres` to `ha` in farm forms
- **Auth pattern**: replaced inline `if 'user_id' not in session` checks with reusable decorators across all blueprints

### Fixed
- **Error handlers**: Added 500 and generic Exception handlers in `app/__init__.py` with proper logging
- **Form values**: Preserved during calculation errors in Farm Add modal
- **Removed debug prints**: Cleaned up legacy debug `print()` statements

## [0.8.0] - 2026-05-09

### Added
- Added FarmModel in validation.py with fields: farm_id, farm_number, name, description, location, boundary, irrigation_system, metadata, statistics, sectors
- Added farms blueprint (`app/blueprints/farms.py`) with full CRUD operations
- Added farms to data hierarchy: Lands → Farms → Sectors → Zones → Rows → Trees
- Added VisitModel in validation.py with fields: visit_id, tree_id, visit_date, visit_type, inspector, status, findings, actions_taken, next_visit, metadata
- Added visits blueprint (`app/blueprints/visits.py`) for tree visit/inspection logging
- Added coordinate calculation (area/perimeter) support for farms

### Changed
- Updated LandModel to include farms array between land and sectors
- Data structure now properly follows PROMPT.md specification with farms as a hierarchy level

### Fixed
- Registered missing farms_bp and visits_bp blueprints in app/__init__.py

## [0.7.0] - 2026-05-04

### Added
- Owner Information group in Add/Edit Land Basic Info tab
- Party ID field for owner identification
- Grouped owner fields (Party ID, Name, Email, Phone) in UI
- Bootstrap Tabs in Add Land modal (Basic Info, Address & Location, Legal Documents, Photos)
- Photos tab with multiple file upload support
- Backend photo upload handling (saved to static/uploads/lands/)
- Light/Dark theme toggle buttons in sidebar (btn-group)
- ZERO state pages for all modules (Lands, Sectors, Zones, Rows, Trees)
- Language buttons organized in btn-group structure
- Inline form replaced with modal for Add Land

### Changed
- Backend now uses form-submitted Party ID instead of hardcoded value
- Updated Add/Edit Land modals to align with LandModel owner structure
- Updated Land layout to match exact JSON structure (postal_code, delivered, legal.types array)
- Login page styled with Bootstrap theme and custom.css
- Language switcher uses btn-outline-light with active state
- Sidebar footer reorganized with grouped buttons

### Fixed
- Addressed template syntax and routing issues
- Template syntax error (duplicate if blocks)
- Removed duplicate Add Land form
- Proper tab navigation with Bootstrap 5 structure

## [0.5.0] - 2026-05-03

### Added
- Refactored all blueprints to use validation.py Pydantic models
- TreeModel integration with fields: tree_id, basic_info, location_precise, metadata
- RowModel integration with fields: row_number, position, tree_count, maintenance
- ZoneModel integration with fields: zone_id, location, statistics, soil_characteristics
- SectorModel integration with fields: sector_id, location, statistics
- LandModel integration with fields: farm_id, location, legal, owner, metadata
- Bulk add functionality for sectors, zones, rows, and trees
- Updated all forms to match validation.py structure
- Added tree_number, species, variety fields to tree forms
- Added latitude/longitude fields for precise tree location
- Enhanced templates to display all new fields

### Changed
- Updated tree forms: crop_variety now maps to basic_info.variety
- Updated tree status to use metadata.status
- Updated tree location to use location_precise.latitude/longitude
- Improved form validation using Pydantic models
- Better error handling in all blueprint routes

### Fixed
- Syntax errors in blueprint files
- Incorrect field mappings between forms and models
- Blueprint registration issues
- Template rendering errors

## [0.4.0] - 2026-05-02

### Added
- Full CRUD operations for all hierarchy levels (Sectors, Zones, Rows, Trees)
- Dedicated detail pages for each entity with breadcrumb navigation
- Edit functionality for sectors, zones, rows, and trees
- Delete functionality with confirmation for all entities
- Proper navigation: Land → Sector → Zone → Row → Tree
- Back buttons on all detail/edit pages
- Admin-only access for edit/delete operations
- Logging for all create/update/delete operations
- Added missing translations for "rows", "trees", "zones"

### Fixed
- Indentation error in app initialization
- Blueprint registration for all hierarchy levels
- Proper ObjectId handling in all new routes
- Template paths for new blueprints
