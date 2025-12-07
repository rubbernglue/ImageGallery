# ImageArchive

A web-based film photography archive management system with a Python Flask API backend, PostgreSQL database, and vanilla JavaScript frontend.

## Features

- Browse and search film photography archives
- Tag images with custom keywords
- Add descriptions to images
- Filter by film type and search by keywords
- Responsive gallery view with modal detail view

## Tech Stack

- **Backend**: Python 3, Flask, psycopg2
- **Database**: PostgreSQL
- **Frontend**: Vanilla JavaScript, Tailwind CSS (CDN)
- **Image Storage**: File system with configurable paths

## Prerequisites

- Python 3.7+
- PostgreSQL 12+
- Film image library organized in the expected structure (see below)

## Installation

1. **Clone the repository**
   ```bash
   cd /home/johan/src/ImageArchive
   ```

2. **Install Python dependencies**
   ```bash
   pip install flask flask-cors psycopg2-binary
   ```

3. **Configure PostgreSQL**
   
   Update the database credentials in both `setup_database.py` and `api_server.py`:
   ```python
   DB_CONFIG = {
       'database': 'imagearchive',
       'user': 'postgres',
       'password': 'your_password_here',  # Change this!
       'host': 'localhost',
       'port': '5432'
   }
   ```

## Setup

### 1. Scan Your Image Library

The scanner expects images organized in this structure:
```
/opt/media/
├── rollfilm/
│   └── batch_name/
│       └── image_base_name/
│           ├── 600/image.jpg    (thumbnail)
│           └── 2560/image.jpg   (high-res)
└── sheetfilm/
    └── batch_name/
        └── image_base_name/
            ├── 600/image.jpg
            └── 2560/image.jpg
```

Update `BASE_DIR` in `library_scanner.py` if your images are in a different location, then run:

```bash
python library_scanner.py
```

This generates `image_data.json` with metadata about all your images.

### 2. Initialize the Database

Run the setup script to create the database and populate it:

```bash
python setup_database.py
```

This will:
- Create the `imagearchive` database
- Create all required tables (images, tags, image_tags)
- Populate the database from `image_data.json`

### 3. Start the API Server

```bash
python api_server.py
```

The API will be available at `http://localhost:5000`

### 4. Open the Frontend

Simply open `image_gallery.html` in your web browser:

```bash
# On Linux
xdg-open image_gallery.html

# On macOS
open image_gallery.html

# On Windows
start image_gallery.html
```

Or just double-click the file in your file manager.

## API Endpoints

- `GET /api/images` - List all images with metadata and tags
- `GET /api/images/<image_id>` - Get single image details
- `PUT /api/images/<image_id>/description` - Update image description
- `PUT /api/images/<image_id>/tags` - Update image tags (replaces all)
- `POST /api/images/<image_id>/tags` - Update image tags (alternative method)

## Configuration

### Image Path Mapping

The frontend converts file system paths to web URLs. By default:
- File system: `/opt/media/...`
- Web URL: `/media/...`

Update the `filePathToWebUrl()` function in `image_gallery.html` if your paths differ.

### API Base URL

The frontend connects to the API at `http://localhost:5000` by default. Update `API_BASE_URL` in `image_gallery.html` if deploying to a different host.

## Database Schema

The database consists of three main tables:

- **images**: Core image metadata (paths, film type, description, etc.)
- **tags**: Unique tag names
- **image_tags**: Many-to-many relationship between images and tags

See `database_schema.sql` for the complete schema.

## Development

### Re-scanning Images

If you add new images to your library:

```bash
python library_scanner.py
python setup_database.py  # Re-run to add new images
```

### Resetting the Database

To start fresh:

```sql
DROP DATABASE imagearchive;
```

Then re-run `python setup_database.py`

## Troubleshooting

**Frontend shows "Could not load required image data from API"**
- Make sure the API server is running (`python api_server.py`)
- Check that `API_BASE_URL` in `image_gallery.html` matches your server
- Check browser console for CORS errors

**Database connection errors**
- Verify PostgreSQL is running: `pg_isready`
- Check credentials in `DB_CONFIG`
- Ensure the database exists: `psql -U postgres -l | grep imagearchive`

**Images not displaying**
- Verify image paths in the database match your file system
- Check `filePathToWebUrl()` mapping in the frontend
- Ensure images are accessible at the mapped URL paths

## License

MIT License - feel free to use and modify for your own projects.
