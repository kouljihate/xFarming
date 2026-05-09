# SmartFarmerFlow - Version History

## [0.7.80] - 2026-05-09

### Added
- Automated version bump for commit


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


## [0.7.79] - 2026-05-08

### Added
- Automated version bump for commit


## [0.7.78] - 2026-05-08

### Added
- Automated version bump for commit


## [0.7.77] - 2026-05-08

### Fixed
- Fixed Add Land modal freeze issue when clicking Calculate button
- Simplified calculation.py to remove external dependencies (pyproj/shapely)
- Fixed route to use `request.form.get('calculate')` directly
- Updated template button to use `name="calculate" value="1"`


## [0.7.76] - 2026-05-08

### Added
- Added coordinate calculation utility for Area/Perimeter

### Changed
- Updated parse_simple_coordinates() to support negative and decimal coordinates


## [0.7.75] - 2026-05-08

### Added
- New calculation utility module (app/utils/calculation.py) for polygon area and perimeter calculations
- Added coordinate parsing to support format: [(x, y), (x, y), ...] with negative and decimal numbers
- Calculate button in Add Land modal (Address & Location tab) to compute Area and Perimeter from coordinates
- Calculate button in Add Sector modal with same functionality

### Changed
- Updated parse_simple_coordinates() to support negative and decimal coordinates
- Auto-open modal after calculation using CSS classes instead of JavaScript

### Fixed
- Fixed pyautogui import error in lands.py


## [0.7.74] - 2026-05-07

### Added
- Automated version bump for commit


## [0.7.73] - 2026-05-07

### Added
- Automated version bump for commit


## [0.7.71] - 2026-05-07

### Added
- Automated version bump for commit


## [0.7.69] - 2026-05-07

### Added
- Automated version bump for commit


## [0.7.68] - 2026-05-07

### Added
- Automated version bump for commit


## [0.7.66] - 2026-05-07

### Added
- Automated version bump for commit


## [0.7.64] - 2026-05-07

### Added
- Automated version bump for commit


## [0.7.62] - 2026-05-07

### Added
- Automated version bump for commit


## [0.7.60] - 2026-05-07

### Added
- Automated version bump for commit


## [0.7.58] - 2026-05-07

### Added
- Automated version bump for commit


## [0.7.56] - 2026-05-06

### Added
- Automated version bump for commit


## [0.7.54] - 2026-05-06

### Added
- Automated version bump for commit


## [0.7.52] - 2026-05-06

### Added
- Automated version bump for commit


## [0.7.50] - 2026-05-06

### Added
- Automated version bump for commit


## [0.7.48] - 2026-05-06

### Added
- Automated version bump for commit


## [0.7.46] - 2026-05-06

### Added
- Automated version bump for commit


## [0.7.45] - 2026-05-06

### Added
- Automated version bump for commit


## [0.7.43] - 2026-05-06

### Added
- Automated version bump for commit


## [0.7.41] - 2026-05-06

### Added
- Automated version bump for commit


## [0.7.39] - 2026-05-06

### Added
- Automated version bump for commit


## [0.7.37] - 2026-05-06

### Added
- Automated version bump for commit


## [0.7.35] - 2026-05-06

### Added
- Automated version bump for commit


## [0.7.33] - 2026-05-06

### Added
- Automated version bump for commit


## [0.7.31] - 2026-05-06

### Added
- Automated version bump for commit


## [0.7.29] - 2026-05-06

### Added
- Automated version bump for commit


## [0.7.27] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.26] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.25] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.24] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.23] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.22] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.21] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.20] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.19] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.18] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.17] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.16] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.15] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.14] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.13] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.12] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.11] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.10] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.9] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.8] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.7] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.6] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.5] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.4] - 2026-05-05

### Added
- Automated version bump for commit


## [0.7.2] - 2026-05-04

### Added
- Automated version bump for commit


## [0.7.1] - 2026-05-04

### Added
- Automated version bump for commit


## [0.7.0] - 2026-05-04

### Added
- Owner Information group in Add/Edit Land Basic Info tab
- Party ID field for owner identification
- Grouped owner fields (Party ID, Name, Email, Phone) in UI

### Changed
- Backend now uses form-submitted Party ID instead of hardcoded value
- Updated Add/Edit Land modals to align with LandModel owner structure

### Fixed
- Addressed template syntax and routing issues

## [0.6.0] - 2026-05-04

### Added
- Bootstrap Tabs in Add Land modal (Basic Info, Address & Location, Legal Documents, Photos)
- Photos tab with multiple file upload support
- Backend photo upload handling (saved to static/uploads/lands/)
- Photo descriptions linked to each uploaded image
- Light/Dark theme toggle buttons in sidebar (btn-group)
- ZERO state pages for all modules (Lands, Sectors, Zones, Rows, Trees)
- Language buttons organized in btn-group structure
- Inline form replaced with modal for Add Land

### Changed
- Updated Land layout to match exact JSON structure (postal_code, delivered, legal.types array)
- Login page styled with Bootstrap theme and custom.css
- Language switcher uses btn-outline-light with active state
- Sidebar footer reorganized with grouped buttons

### Fixed
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
