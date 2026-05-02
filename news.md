# xFarming - Version History

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
