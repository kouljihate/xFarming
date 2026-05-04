# xFarming - Version History

## [0.7.0] - 2026-05-04

### Added
- Updated multiple templates and static assets
- Modified translations and data models
- Enhanced UI/UX components

### Changed
- Refactored blueprint logic and template structures
- Updated custom CSS styles

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
