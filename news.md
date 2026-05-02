# xFarming - Version History

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

### Technical Details
- Created separate blueprints: sectors, zones, rows, trees
- Each entity has detail, edit, and delete routes
- Breadcrumb navigation: Land > Sector > Zone > Row > Tree
- All delete operations use POST method for security
- Integrated with logging system (info/warning levels)

## [0.3.0] - 2026-05-02

### Added
- Enhanced navigation bar with logo (🌾 xFarming) and role-based links
- Navigation links now show Dashboard, Lands, Activities for all users
- Admin-only links for User Management in navbar
- Custom 404 error page with friendly UI and navigation back to dashboard
- Auto-dismissing flash messages (3 seconds timeout)
- RTL (Right-to-Left) support for Arabic language
- 3-level log system (info, warning, error) with MongoDB storage
- Admin-only log viewer with filtering by log level
- Colored stat cards on dashboard with icons and shadows
- "View All" link on dashboard recent activities section
- Log filtering buttons (Info/Warning/Error/All)

### Fixed
- Base template now properly handles RTL languages
- Flash messages auto-dismiss with JavaScript
- Dashboard stat cards now use consistent styling with Bootstrap shadows

### Technical Details
- Created `app/utils/logging.py` for centralized logging
- Added 404 error handler registration in app factory
- Navigation conditionally displays based on user role
- Log viewer supports pagination (50 logs per page)

## [0.2.0] - 2026-05-02

### Added
- Complete CRUD operations for all hierarchical entities (Lands, Sectors, Zones, Rows, Trees)
- Modal forms for adding new entities at each level
- Activity logging for all create operations
- Fixed ObjectId handling across all blueprints and templates
- Added missing translations for all languages (EN/AR/FR)
- Simplified dashboard without Plotly dependency (ready for future integration)
- Test script for verifying application setup

### Fixed
- ObjectId serialization issues in templates
- Missing translation keys for hierarchical structure labels
- Dashboard import errors when Plotly not installed
- User management ObjectId handling

### Technical Details
- Proper ObjectId to string conversion for template rendering
- Activity logging with datetime stamps
- Form modals for each hierarchical level
- Multi-language support throughout all entities

## [0.1.0] - 2026-05-02

### Added
- Initial project structure with Flask and MongoDB
- Authentication system with role-based access (guest, worker, admin, customer)
- Dashboard with statistics cards and Plotly treemap visualization
- Lands management with Folium maps integration
- Land detail page with hierarchical view (Lands → Sectors → Zones → Rows → Trees)
- Activities pagination (20 per page)
- User management interface (admin only)
- Multi-language support (English, Arabic, French)
- Light/Dark theme toggle with Bootstrap 5.3.3 + Bootswatch Minty
- Flash messages for user feedback
- Responsive design with Bootstrap cards and navigation

### Technical Details
- Server-side rendering with Jinja2 templates (no JavaScript SPA)
- MongoDB with PyMongo for data persistence
- Blueprint architecture for modular code organization
- Session-based authentication
- Translation system with centralized translations.py
