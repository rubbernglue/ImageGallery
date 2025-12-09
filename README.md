# ImageArchive

A web-based film photography archive management system with a Python Flask API backend, PostgreSQL database, and vanilla JavaScript frontend.

## Features

- **Browse & Search**: View all images with search by keywords, tags, film type, and stock
- **User Authentication**: Secure login system with token-based auth
- **Read-Only for Guests**: Anyone can browse, only logged-in users can edit
- **Tag Management**: Add/remove tags on single or multiple images at once
- **Bulk Operations**: Select multiple images and tag them all at once
- **Descriptions**: Add detailed descriptions to images
- **Incremental Updates**: Add new image batches without rewriting entire database
- **Responsive Design**: Works on desktop and mobile devices

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

## Security & Authentication

### Setting Up User Accounts

1. **Generate secure password hashes**:
   ```bash
   python generate_password_hash.py
   ```
   Follow the prompts to create a username and password.

2. **Update api_server.py** with the generated hash:
   Edit the `USERS` dictionary in `api_server.py` and replace the default credentials.

3. **Change the SECRET_KEY** in `api_server.py`:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   Copy the output and update `SECRET_KEY` in `api_server.py`.

### Default Credentials (⚠️ CHANGE IMMEDIATELY!)
- Username: `admin` / Password: `admin123`
- Username: `user1` / Password: `password1`

### Security Features
- PBKDF2 password hashing with 100,000 iterations
- Token-based authentication with 24-hour expiration
- Constant-time password comparison (prevents timing attacks)
- HTTPS support via nginx reverse proxy
- Read-only access for non-authenticated users

## Updating the Database

### Adding New Images

**Option 1: Update from full scan**
```bash
python library_scanner.py  # Scan all images
python update_database.py  # Add new images to database
```

**Option 2: Update specific subdirectory**
```bash
python update_database.py --scan-dir /opt/media/rollfilm 645_2025_Nikon_med_Ilford
```

**Option 3: Update from existing JSON**
```bash
python update_database.py --json my_images.json
```

The update script only adds new images and skips existing ones, preserving all tags and descriptions.

## Usage Guide

### For Everyone (No Login Required)
- Browse all images in the gallery
- Search by keywords, tags, film stock, or batch name
- Filter by film type (roll/sheet film)
- Click images to view full resolution
- Download high-res images

### For Logged-In Users
All the above, plus:
- Add/remove tags on images
- Edit descriptions
- **Multi-Select Mode**: Select multiple images and tag them all at once
  1. Click "Select Multiple" button
  2. Click images to select them (blue outline appears)
  3. Click "Add Tags to Selected"
  4. Enter comma-separated tags
  5. Tags are added to all selected images

### Multi-Image Tagging Example
```
1. Enable Select Mode
2. Select 10 images from a specific batch
3. Add tags: "vacation, 2024, italy"
4. All 10 images now have these tags
```

## Nginx Configuration

For HTTPS support and proper proxying:

1. Copy `nginx_imagearchive.conf` to your nginx sites directory
2. Update paths and domain name
3. Test and reload:
   ```bash
   sudo nginx -t
   sudo nginx -s reload
   ```

The configuration includes:
- HTTPS redirect
- API reverse proxy with caching
- Static file serving for images
- Proper CORS and security headers

