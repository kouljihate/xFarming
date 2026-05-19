# SmartFarmerFlow - AI Development Prompt

## Project Overview

**SmartFarmerFlow** is a Flask-based agricultural land management web application with MongoDB. It manages hierarchical farm data: Lands → Farms → Sectors → Zones → Rows → Trees.

- **Version**: 0.9.3
- **Framework**: Flask with Blueprint modular architecture
- **Database**: MongoDB (pymongo)
- **Validation**: Pydantic v2
- **Templates**: Jinja2 with Bootstrap 5 (Bootswatch themes)
- **Languages**: English, Arabic (RTL), French
- **No JavaScript**: All visualizations generated server-side (Plotly, Folium)

---

## Architecture

### Directory Structure
```
SFarming/
├── app/
│   ├── blueprints/          # Flask blueprints
│   │   ├── auth.py          # Authentication (login/logout)
│   │   ├── dashboard.py     # Main dashboard with maps/stats
│   │   ├── lands.py         # Land management
│   │   ├── farms.py         # Farm management
│   │   ├── sectors.py       # Sector management
│   │   ├── zones.py         # Zone management
│   │   ├── rows.py          # Row management
│   │   ├── trees.py         # Tree management
│   │   ├── visits.py        # Tree visit/inspection logging
│   │   ├── activities.py    # Activity logging
│   │   └── users.py         # User management
│   ├── models/
│   │   ├── __init__.py      # Legacy Land/Activity classes
│   │   └── validation.py     # Pydantic models (primary)
│   ├── templates/           # Jinja2 templates
│   ├── utils/
│   │   ├── logging.py       # Logging to MongoDB
│   │   └── calculation.py   # Polygon area/perimeter calculation
│   ├── __init__.py          # App factory (create_app)
│   ├── config.py            # Configuration
│   ├── database.py          # MongoDB connection
│   └── translations.py     # i18n translations
├── static/uploads/         # Uploaded files
├── run.py                   # Entry point
└── init_data.py            # Database initialization
```

### Data Storage Pattern

All hierarchy data stored as **nested arrays within lands collection**:
- Single `lands` collection
- Each land document contains `farms` array
- Each farm document contains `sectors` array
- Each sector contains `zones` array
- Each zone contains `rows` array
- Each row contains `trees` array
- Each tree contains `visits` array


lands collection document:
{
  _id: ObjectId,
  name: "Land Name",
  location: { coordinates: { latitude, longitude }, ... },
  farms: [
    {
      _id: "farm_id",
      name: "Farm 1",
      sectors: [
        {
          _id: "sector_id",
          name: "Sector 1",
          zones: [
            {
              _id: "zone_id",
              name: "Zone A",
              rows: [
                {
                  _id: "row_id",
                  name: "Row 1",
                  trees: [
                    { _id: "tree_id", name: "Tree 1", visits: [...], ... }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

---

## Function/Class Reference

### Core Application

#### `create_app()` in `app/__init__.py`
- Flask application factory
- Initializes Bootstrap, logging, translations
- Registers all blueprints (auth, dashboard, lands, activities, users, sectors, zones, rows, trees)
- Sets up Jinja globals: `t` (translation function), `app_version`

#### `Config` class in `app/config.py`
- `SECRET_KEY`: Flask secret key
- `MONGO_URI`: MongoDB connection string
- `FLASK_ENV`: Environment (development/production)

#### `get_db()` in `app/database.py`
- Returns MongoDB database instance
- Uses `current_app.config['MONGO_URI']`

#### `init_db()` in `app/database.py`
- Creates 'users' collection with default admin user (admin/admin123)

#### `t(key, lang)` in `app/translations.py`
- Translation function returning translated string for given key/language
- Supported languages: 'en', 'ar' (Arabic), 'fr' (French)

### Validation Models (`app/models/validation.py`)

#### `TreeModel(BaseModel)`
- `tree_id`: str (e.g., "T001")
- `position_in_row`: int
- `tree_number`: str
- `qr_code`: Optional[str]
- `rfid_tag`: Optional[str]
- `basic_info`: dict (species, common_name, scientific_name, variety, rootstock, clone_id, source, source_certified, planting_date, planted_by, age_years, expected_lifespan_years, generation)
- `location_precise`: dict (latitude, longitude, altitude_meters, accuracy_cm, slope_percentage, aspect, distances)
- `visits`: List[dict]
- `historical_production`: List[dict]
- `irigation_record`: List[dict] (note: typo "irigation")
- `photos`: List[dict]
- `notes`: List[dict]
- `metadata`: dict (created_date, last_updated, status, notes, version, data_quality_score, sync_status, backup_location)

#### `RowModel(BaseModel)`
- `row_number`: int (default=1)
- `name`: str (default="Row")
- `description`: Optional[str]
- `position`: dict (start_coordinates, end_coordinates, length, orientation)
- `tree_count`: dict (total_positions, active_trees, empty_positions, dead_trees, replacement_needed)
- `maintenance`: dict (last_pruned, last_fertilized, last_irrigated, next_maintenance, maintenance_notes)
- `metadata`: dict (created_date, last_updated, status, notes)
- `trees`: List[TreeModel]

#### `ZoneModel(BaseModel)`
- `zone_id`: str
- `zone_number`: str
- `name`: str (required, 1-100 chars)
- `description`: Optional[str]
- `location`: dict (area, row_spacing, tree_spacing, orientation)
- `boundary`: dict (type: "Polygon", coordinates)
- `crop_info`: dict (current_crop, variety, planting_date, rootstock, pollinators)
- `soil_characteristics`: dict (type, ph, organic_matter, drainage)
- `statistics`: dict (total_rows, total_trees, trees_per_acre, active_trees, dead_trees, replacement_rate)
- `maintenance`: dict
- `metadata`: dict (created_date, last_updated, status, notes, zone_manager)
- `rows`: List[RowModel]

#### `SectorModel(BaseModel)`
- `sector_id`: str
- `sector_number`: int (default=1)
- `name`: str (required, 1-100 chars)
- `description`: Optional[str]
- `location`: dict (area, soil_type, slope, irrigation_type)
- `boundary`: dict (type: "Polygon", coordinates)
- `metadata`: dict (created_date, last_updated, status, notes, version)
- `statistics`: dict (total_zones, total_rows, total_trees)
- `zones`: List[ZoneModel]

#### `LandModel(BaseModel)`
- `farm_id`: str (max 50 chars)
- `name`: str (required, no empty/whitespace)
- `legal`: dict (type: list of strings, deleivered, date) - note: typo "deleivered"
- `owner`: dict (party_id, name, contact: {email, phone})
- `location`: dict (address: {street, city, state, postal_code, country}, coordinates: {latitude, longitude}, total_area: {value, unit}, boundary)
- `metadata`: dict (established_date, last_updated, status)
- `farms`: List[FarmModel]
- `check_duplicate(db, name, exclude_id)`: Static method to prevent duplicate land names

#### `FarmModel(BaseModel)`
- `farm_id`: str
- `farm_number`: int (default=1)
- `name`: str (required, 1-100 chars)
- `description`: Optional[str]
- `location`: dict (area, soil_type, topography, climate_zone)
- `boundary`: dict (type: "Polygon", coordinates)
- `irrigation_system`: dict (type, source, capacity_lph, notes)
- `metadata`: dict (created_date, last_updated, status, notes, version)
- `statistics`: dict (total_sectors, total_zones, total_rows, total_trees, cultivated_area)
- `sectors`: List[SectorModel]

#### `VisitModel(BaseModel)`
- `visit_id`: str
- `tree_id`: Optional[str]
- `visit_date`: str
- `visit_type`: str (default="inspection")
- `inspector`: Optional[str]
- `status`: str (default="pending")
- `findings`: dict (health_status, pests, diseases, notes)
- `actions_taken`: List[dict]
- `next_visit`: Optional[str]
- `metadata`: dict (created_date, last_updated, version)

#### `ActivityModel(BaseModel)`
- `type`: str (pattern: irrigating|fertilizing|harvesting|planting|pruning)
- `notes`: Optional[str]
- `date`: Optional[datetime]

#### `UserModel(BaseModel)`
- `username`: str (3-50 chars)
- `password`: str (min 4 chars)
- `role`: str (pattern: guest|worker|admin|customer)

### Blueprint Routes

#### `auth_bp` (`app/blueprints/auth.py`)
- `GET/POST /auth/login` → `login()`: Authenticates user, sets session (user_id, username, role)
- `GET /auth/logout` → `logout()`: Clears session

#### `dashboard_bp` (`app/blueprints/dashboard.py`)
- `GET /dashboard/` → `index()`: Renders dashboard with stats (counts all entities), recent activities, Plotly map of all lands
- `GET /dashboard/set-theme/<theme>` → `set_theme()`: Sets Bootswatch theme (light→minty, dark→darkly)

#### `lands_bp` (`app/blueprints/lands.py`)
- `GET /lands/` → `index()`: Lists all lands with search, generates Folium maps (in List Action column add Add farm button)
- `GET/POST /lands/add` → `add()`: Add land form with coordinate calculation
- `POST /lands/<land_id>/edit` → `edit()`: Edit land (admin only)
- `GET/POST /lands/<land_id>` → `detail()`: Land detail with farms/sectors/zones/rows/trees
- `POST /lands/<land_id>/delete` → `delete()`: Delete land (admin only)
- `POST /lands/<land_id>/upload_photo` → `upload_photo()`: Upload photos to land
- `POST /lands/<land_id>/delete_photo/<filename>` → `delete_photo()`: Delete land photo

#### `farms_bp` (`app/blueprints/farms.py`)
- `GET /farms/` → `index()`: Lists all farms across lands with search
- `POST /farms/add` → `add()`: Add farm to land (admin only, with coordinate calculation)
- `GET /farms/<farm_id>` → `detail()`: Farm detail with sectors
- `GET/POST /farms/<farm_id>/edit` → `edit()`: Edit farm (admin only)
- `POST /farms/<farm_id>/delete` → `delete()`: Delete farm (admin only)
- `POST /farms/bulk_add` → `bulk_add()`: Add multiple farms with prefix/range

#### `sectors_bp` (`app/blueprints/sectors.py`)
- `GET /sectors/` → `index()`: Lists all sectors across lands with search
- `POST /sectors/add` → `add()`: Add sector to land (admin only)
- `GET /sectors/<sector_id>` → `detail()`: Sector detail with zones
- `GET/POST /sectors/<sector_id>/edit` → `edit()`: Edit sector (admin only)
- `POST /sectors/<sector_id>/delete` → `delete()`: Delete sector (admin only)
- `POST /sectors/bulk_add` → `bulk_add()`: Add multiple sectors with prefix/range

#### `zones_bp` (`app/blueprints/zones.py`)
- `GET /zones/` → `index()`: Lists all zones across sectors
- `POST /zones/add` → `add()`: Add zone to sector (admin only)
- `GET /zones/<zone_id>` → `detail()`: Zone detail with rows
- `POST /zones/<zone_id>/edit` → `edit()`: Edit zone (admin only)
- `POST /zones/bulk_add` → `bulk_add()`: Add multiple zones from newline-separated names

#### `rows_bp` (`app/blueprints/rows.py`)
- `GET /rows/` → `index()`: Lists all rows across zones
- `POST /rows/add` → `add()`: Add row to zone (admin only)
- `GET /rows/<row_id>` → `detail()`: Row detail with trees
- `POST /rows/<row_id>/edit` → `edit()`: Edit row (admin only)
- `POST /rows/bulk_add` → `bulk_add()`: Add multiple rows from newline-separated names

#### `trees_bp` (`app/blueprints/trees.py`)
- `GET /trees/` → `index()`: Lists all trees across rows
- `POST /trees/add` → `add()`: Add tree to row (admin only)
- `GET /trees/<tree_id>` → `detail()`: Tree detail view
- `POST /trees/<tree_id>/edit` → `edit()`: Edit tree (admin only)
- `POST /trees/<tree_id>/delete` → `delete()`: Delete tree (admin only)
- `POST /trees/bulk_add` → `bulk_add()`: Add multiple trees with count

#### `visits_bp` (`app/blueprints/visits.py`)
- `GET /visits/` → `index()`: Lists all visits across trees (paginated, 20 per page)
- `POST /visits/add` → `add()`: Add visit to tree (admin/worker)
- `GET /visits/<visit_id>` → `detail()`: Visit detail view
- `GET/POST /visits/<visit_id>/edit` → `edit()`: Edit visit (admin/worker)
- `POST /visits/<visit_id>/delete` → `delete()`: Delete visit (admin only)

#### `activities_bp` (`app/blueprints/activities.py`)
- `GET/POST /activities/add` → `add()`: Add activity record
- `GET /activities/` → `index()`: Paginated activity list (20 per page)

#### `users_bp` (`app/blueprints/users.py`)
- `GET /users/` → `index()`: List all users (admin only)
- `POST /users/change-role/<user_id>` → `change_role()`: Change user role (admin only)
- `POST /users/delete/<user_id>` → `delete()`: Delete user (admin only)
- `GET /users/logs` → `view_logs()`: View system logs (admin only, paginated)

### Utility Modules

#### `log_message(level, message, user_id, username)` in `app/utils/logging.py`
- Logs message to MongoDB 'logs' collection
- Levels: 'info', 'warning', 'error'


#### `get_logs(page, per_page, level)` in `app/utils/logging.py`
- Returns paginated logs with total count

#### `setup_logging(app)` in `app/utils/logging.py`
- Sets up file handler (rotating, 10MB, 10 backups) and colored console handler
- Log file: logs/SmartFarmerFlow.log

#### `ColorFormatter` class in `app/utils/logging.py`
- Custom logging formatter with color codes

#### `calculate_distance(p1, p2)` in `app/utils/calculation.py`
- Euclidean distance between two 2D points

#### `calculate_perimeter(coordinates)` in `app/utils/calculation.py`
- Sum of edge lengths of polygon (closes automatically)

#### `calculate_area(coordinates)` in `app/utils/calculation.py`
- Shoelace formula for polygon area

#### `parse_simple_coordinates(input_str)` in `app/utils/calculation.py`
- Parses format: `[(x1, y1), (x2, y2), ...]`
- Returns list of [x, y] pairs or None

#### `calculate_polygon_from_boundary(boundary_json)` in `app/utils/calculation.py`
- Accepts GeoJSON Polygon, returns {area, perimeter}

#### `convert_and_calculate(coordinates_str)` in `app/utils/calculation.py`
- Full conversion: parse → calculate → return {area, perimeter, geojson}

### Legacy Models (`app/models/__init__.py`)

#### `Land` class
- Simple land model with to_dict() method
- Used by activities.py for activity logging

#### `Activity` class
- Activity model with type, notes, date
- to_dict() method for MongoDB insertion

---

## Key Patterns

### Authentication/Authorization
- Session-based auth with `user_id`, `username`, `role`
- Admin-only: lands.add, sectors.add, zones.add, rows.add, trees.add (POST methods)
- Session check on all routes with redirect to login

### Pydantic v2 Usage
- Use `model_dump()` (NOT `.dict()`) for serialization
- Use `Field(default_factory=lambda: {...})` for nested dict defaults
- Validate with `model.model_validate(form_data)` or direct instantiation

### MongoDB Operations
- `ObjectId()` for generating new IDs (stored as strings)
- `db.lands.update_one({'_id': ObjectId(id)}, {'$set': {...}})`
- `$push` for adding to arrays
- Nested array updates use array filters: `{'$push': {'sectors.$[elem].zones': zone_dict}}`

### Template Patterns
- Extend `base.html`
- Bootstrap 5 with Bootswatch theme (minty/darkly)
- Modal forms for Add/Edit
- Sidebar navigation with breadcrumbs
- Translations via `{{ t('key') }}`

### Role-based Access
- `admin`: Full access (CRUD on all entities)
- `worker`: Can add/view lands, sectors, upload photos
- `guest`, `customer`: View-only (authenticated)


### Bulk Operations
- Accept newline-separated names
- Generate multiple entities with sequential numbering
- Prefix/suffix support

---

## Development Rules

1. **NO JavaScript**: All functionality in Python
2. **No external map libraries** except python-plotly Maps (server-side)
3. **Use Pydantic** for all validation
4. **Nested storage**: All hierarchy in lands collection
5. **Server-side charts**: Use Plotly generated HTML
6. **Server-side maps**: Use python-plotly Maps generated HTML

---

## Common Field Mappings

| Entity | Display Field | ID Field | Status Field |
|--------|---------------|----------|--------------|
| Tree | `basic_info.variety` | `tree_id` | `metadata.status` |
| Tree | `name`    | `tree_id` | - |
| Row | `name`    | `row_id` | `metadata.status` |
| Zone | `name`    | `zone_id` | `metadata.status` |
| Sector | `name`    | `sector_id` | `metadata.status` |
| Farm | `name`    | `farm_id` | `metadata.status` |
| Land | `name`    | `land_id` | `metadata.status` |
---

## Example Request Flow

**Adding a Tree:**
1. User POSTs to `/trees/add` with row_id
2. Blueprint validates with TreeModel
3. Uses `$push` with array filters to add to correct row
4. Logs db Action into db log collection
5. Logs action into Flask log and text log file
6. Redirects to `/trees/`

**Bulk Add Sectors:**
1. POST to `/sectors/bulk_add` with land_id, prefix, start, end
2. Generate names: [f"{prefix} {i}" for i in range(start, end+1)]
3. Validate each with SectorModel
4. Append to land's sectors array
5. Single update to MongoDB