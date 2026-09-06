# SmartFarmerFlow - Smart Farm Management System

A Flask-based web application for managing agricultural lands with hierarchical structure: Lands → Farms → Sectors → Zones → Rows → Trees.

## Features

- **Multi-level Hierarchy Management**: Organize lands into sectors, zones, rows, and individual trees
- **Pydantic Validation**: All data models validated using `validation.py` with strict schemas
- **Bulk Operations**: Add multiple sectors, zones, rows, or trees at once
- **Role-based Access**: Admin and worker roles with proper permissions
- **Multilingual Support**: English, Arabic, and French translations
- **Theme Customization**: Multiple Bootstrap themes with dark/light modes
- **Interactive Maps**: Plotly-based satellite maps for farm visualization
- **Boundary Management**: GeoJSON polygon boundaries with area/perimeter calculation
- **Activity Logging**: Track all create/update/delete operations
- **Database Flexibility**: Handles both ObjectId and string _id formats for MongoDB compatibility

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd SmartFarmerFlow

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your MongoDB connection string and secret key

# Initialize the database
python init_data.py

# Run the application
python run.py
```

## Project Structure

```
SFarming/
├── app/
│   ├── blueprints/          # Flask blueprints for each module
│   │   ├── auth.py
│   │   ├── lands.py        # Land management (uses LandModel)
│   │   ├── farms.py       # Farm management (uses FarmModel)
│   │   ├── sectors.py      # Sector management (uses SectorModel)
│   │   ├── zones.py        # Zone management (uses ZoneModel)
│   │   ├── rows.py         # Row management (uses RowModel)
│   │   ├── trees.py        # Tree management (uses TreeModel)
│   │   ├── visits.py       # Tree visits/inspections (uses VisitModel)
│   │   ├── dashboard.py
│   │   ├── activities.py
│   │   └── users.py
│   ├── models/
│   │   ├── validation.py   # Pydantic models for all entities
│   │   └── __init__.py
│   ├── templates/          # Jinja2 templates
│   │   ├── base.html
│   │   ├── lands/
│   │   ├── farms/
│   │   ├── sectors/
│   │   ├── zones/
│   │   ├── rows/
│   │   ├── trees/
│   │   └── ...
│   ├── static/
│   │   └── css/custom.css
│   ├── utils/
│   │   ├── logging.py
│   │   ├── calculation.py
│   │   └── map_utils.py
│   ├── database.py
│   ├── translations.py
│   └── __init__.py
├── .env
├── config.py
├── run.py
├── init_data.py
├── requirements.txt
├── CHANGELOG.md
└── README.md
```

## Data Models (validation.py)

The application uses Pydantic models for strict validation:

### LandModel
- `farm_id`, `name`, `location` (coordinates, total_area, boundary)
- `legal`, `owner`, `metadata`, `farms` (list of FarmModel)

### FarmModel
- `farm_id`, `farm_name`, `description`
- `location` (area, soil_type, topography, climate_zone)
- `boundary` (GeoJSON Polygon), `irrigation_system`, `metadata`, `statistics`
- `sectors` (list of SectorModel)

### SectorModel
- `sector_id`, `sector_number`, `name`, `description`
- `location`, `boundary`, `metadata`, `statistics`
- `zones` (list of ZoneModel)

### ZoneModel
- `zone_id`, `zone_number`, `name`, `description`
- `location`, `boundary`, `crop_info`, `soil_characteristics`
- `statistics`, `maintenance`, `metadata`
- `rows` (list of RowModel)

### RowModel
- `row_number`, `name`, `description`, `position`
- `tree_count`, `maintenance`, `metadata`
- `trees` (list of TreeModel)

### TreeModel
- `tree_id`, `position_in_row`, `tree_number`
- `basic_info` (species, variety, planting_date, age_years)
- `location_precise` (latitude, longitude, altitude)
- `visits`, `historical_production`, `irrigation_record`
- `photos`, `notes`, `metadata`

## Usage

1. **Login** with admin credentials (default: admin/admin123)
2. **Add Lands** with coordinates and soil type
3. **Create Farms** within lands
4. **Create Sectors** within farms
5. **Add Zones** within sectors
6. **Create Rows** within zones
7. **Plant Trees** within rows
8. **Log Visits/Inspections** for trees
9. Use **Bulk Add** features for multiple entries

## Key Implementation Details

### Database Layer
- `find_doc(collection, doc_id)` - Universal document lookup that handles both ObjectId and string _id formats
- All blueprints use this helper for consistent MongoDB queries

### Boundary Storage
- Boundaries stored as GeoJSON Polygons: `{"type": "Polygon", "coordinates": [[[lng, lat], ...]]}`
- Calculation utilities support area (hectares), perimeter (meters), and centroid computation

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Version History

### v1.0.1 (2026-09-06)
- Fixed farm delete operation - resolves ObjectId vs string _id mismatch
- Added `find_doc()` helper in database.py for universal document lookup
- Updated all blueprints to use `find_doc()` for MongoDB queries
- Fixed `FarmModel.check_duplicate()` to handle both ID types
- Improved delete endpoint with detailed logging and error messages

### v1.0.0 (2026-05-19)
- Major release with tests, map utils, validation, and UI improvements
- Pydantic v2 validation models for all entities
- Interactive Plotly maps with satellite view
- Bulk operations for all hierarchy levels
- Multi-language support (EN/AR/FR)

See [CHANGELOG.md](CHANGELOG.md) for complete version history.
