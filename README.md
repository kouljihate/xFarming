# SmartFarmerFlow - Smart Farm Management System

A Flask-based web application for managing agricultural lands with hierarchical structure: Lands → Farms → Sectors → Zones → Rows → Trees.

## Development Rules

- **NO JavaScript**: Use ONLY Python for all functionality. All visualizations and maps must be generated server-side (Plotly, etc.) and rendered as HTML.

## Features

- **Multi-level Hierarchy Management**: Organize lands into sectors, zones, rows, and individual trees
- **Pydantic Validation**: All data models validated using `validation.py` with strict schemas
- **Bulk Operations**: Add multiple sectors, zones, rows, or trees at once
- **Role-based Access**: Admin and worker roles with proper permissions
- **Multilingual Support**: English, Arabic, and French translations
- **Theme Customization**: Multiple Bootstrap themes with dark/light modes
- **Interactive Maps**: Folium integration for land visualization
- **Activity Logging**: Track all create/update/delete operations

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
│   │   ├── sectors/
│   │   ├── zones/
│   │   ├── rows/
│   │   ├── trees/
│   │   └── ...
│   ├── static/
│   │   └── css/custom.css
│   ├── utils/
│   ├── database.py
│   ├── translations.py
│   └── __init__.py
├── .env
├── config.py
├── run.py
├── init_data.py
├── requirements.txt
├── news.md               # Version history
└── README.md
```

## Data Models (validation.py)

The application uses Pydantic models for strict validation:

### LandModel
- `farm_id`, `name`, `location` (coordinates, total_area, boundary)
- `legal`, `owner`, `metadata`, `farms` (list of FarmModel)

### FarmModel
- `farm_id`, `farm_number`, `name`, `description`
- `location` (area, soil_type, topography, climate_zone)
- `boundary`, `irrigation_system`, `metadata`, `statistics`
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

## Optimal and Detailed Prompt for AI-Assisted Development

When working with this codebase or creating similar applications, use this detailed prompt:

---

### Prompt Template:

```
I'm building a Flask application for agricultural land management with MongoDB.

**Project Requirements:**
- Use Flask with MongoDB (pymongo)
- Hierarchical data structure: Land → Sector → Zone → Row → Tree
- All data stored in a single 'lands' collection with nested arrays
- Use Pydantic (pydantic v2) for data validation with models in `app/models/validation.py`
- Use Flask blueprints for modular routing
- Use Jinja2 templates with Bootstrap 5 (Bootswatch themes)
- Support English, Arabic (RTL), and French languages
- Role-based access control (admin, worker)
- Bulk add functionality for all hierarchy levels

**Data Model Structure (validation.py):**
```python
class TreeModel(BaseModel):
    tree_id: str = Field(default='')
    position_in_row: int = Field(default=0)
    basic_info: Optional[dict] = Field(default_factory=lambda: {
        'species': '', 'variety': '', 'planting_date': '', 'age_years': 0
    })
    location_precise: Optional[dict] = Field(default_factory=lambda: {
        'latitude': 0.0, 'longitude': 0.0
    })
    metadata: Optional[dict] = Field(default_factory=lambda: {
        'status': 'active', 'created_date': '', 'last_updated': ''
    })
    # ... other fields

class RowModel(BaseModel):
    row_number: int = Field(default=1)
    name: str = Field(default='Row')
    trees: List[TreeModel] = Field(default_factory=list)
    # ... other fields

# Similar for ZoneModel, SectorModel, LandModel
```

**Blueprint Pattern:**
- Each module (lands, sectors, zones, rows, trees) has its own blueprint
- Blueprint format: `module_bp = Blueprint('module', __name__, url_prefix='/module')`
- All create/update operations use Pydantic model validation
- Store data in nested structure within lands collection
- Use `bson.ObjectId` for ID handling

**Template Pattern:**
- Extend `base.html` with sidebar navigation
- Use modals for add/edit forms
- Display data in Bootstrap tables with proper field mapping
- For trees: map `tree.basic_info.variety` to variety field
- For trees: map `tree.metadata.status` to status field
- Show `tree.location_precise.latitude/longitude` for coordinates

**Key Implementation Details:**
1. All entities stored as nested arrays within land document
2. Use `ObjectId()` for generating new IDs (stored as strings)
3. Update parent land document after any nested changes
4. Bulk add: accept newline-separated names, create multiple entities
5. Delete operations: filter out by ID from parent's array
6. Use `model_dump()` (not `.dict()`) for Pydantic v2

**Routes Structure:**
- `/lands/` - List all lands
- `/lands/<land_id>` - Land detail with sectors
- `/sectors/` - List all sectors across all lands
- `/sectors/<sector_id>` - Sector detail with zones
- `/zones/` - List all zones
- `/zones/<zone_id>` - Zone detail with rows
- `/rows/` - List all rows
- `/rows/<row_id>` - Row detail with trees
- `/trees/` - List all trees
- `/trees/<tree_id>` - Tree detail
- `/module/bulk_add` - Bulk add for each module

When adding new features or fixing bugs, maintain this structure and refer to validation.py for field names.
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Version History

### v0.9.1 (2026-05-13)
- Auth decorators (`@login_required`, `@admin_required`, `@log_func_call`) for centralized access control
- Geo calculations: centroid, geodesic area/perimeter using pyproj/shapely WGS84
- Map browsing module with Leaflet.js polygon visualization
- Farms CRUD with legal docs, photo upload, Google Maps integration
- 500 error page and improved error handlers
- LOG_MODE env var for console/file/combined logging
- Farm translations in EN/AR/FR
- Refactored lands/farms blueprints with action-based form handling

### v0.7.73 (2026-05-07)
- Bootstrap Tabs in Add Land modal (Basic Info, Address & Location, Legal Documents, Photos)
- Photos tab with multiple file upload support
- Backend photo upload handling (saved to `static/uploads/lands/`)
- Light/Dark theme toggle buttons in sidebar
- ZERO state pages for all modules (Lands, Sectors, Zones, Rows, Trees)
- Language buttons organized in btn-group structure
- Removed duplicate forms, fixed template syntax errors
- Updated Land layout to match exact JSON structure
- Refactored all blueprints to use validation.py Pydantic models
- TreeModel, RowModel, ZoneModel, SectorModel, LandModel integration
- Bulk add functionality for all hierarchy levels
- Updated forms/templates to match validation.py structure

See [news.md](news.md) for complete version history.
