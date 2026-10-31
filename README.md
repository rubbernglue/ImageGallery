# ImageArchive

A web-based film photography archive management system with a Python Flask API backend, PostgreSQL database, and vanilla JavaScript frontend.

## Features

- **Browse & Search**: View all images with search by keywords, tags, film type, and stock
- **User Authentication**: Secure login system with token-based auth
- **Read-Only for Guests**: Anyone can browse, only logged-in users can edit
- **Tag Management**: Add/remove tags on single or multiple images at once
- **Bulk Operations**: Select multiple images and tag them all at once
- **Descriptions**: Add detailed descriptions to images
- **Favorites**: Each logged-in user can favorite images and filter on them
- **Incremental Updates**: `update_all.py` processes only new/changed images and keeps tags when files are renamed
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
   
   Update the database credentials in `setup_database.py`, `api_server.py` and `update_all.py`:
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

### 1. Initialize the Database

```bash
python setup_database.py
psql -U postgres -d imagearchive -f database_schema_exif.sql
psql -U postgres -d imagearchive -f add_reload_flag.sql
psql -U postgres -d imagearchive -f add_favorites.sql
```

`setup_database.py` creates the database and the core tables; the SQL files add the EXIF
columns, the reload flag and the favorites table. (`update_all.py` adds the `content_hash`
column itself; see `add_content_hash.sql`.)

### 2. Import Your Images

Set the source and library paths at the top of `update_all.py`, then run:

```bash
python update_all.py --dry-run   # see what would happen
python update_all.py
```

It creates 600px and 2560px versions of every source image, reads EXIF and fills the
database. The library ends up organized like this:
```
/opt/media/
├── rollfilm/
│   └── batch_name/
│       └── image_base_name/
│           ├── 600/image_base_name.jpg    (thumbnail)
│           └── 2560/image_base_name.jpg   (high-res)
└── sheetfilm/
    └── ...
```

See `UPDATE_WORKFLOW.md` for all options (renames, orphans, reloading marked images).

### 3. Start the API Server

```bash
python api_server.py
```

The API will be available at `http://localhost:5000`

### 4. Open the Frontend

The frontend (`html/image_gallery.html`) calls the API with relative URLs (`/api/...`) and
loads images from `/media/...`, so serve it through nginx together with the API; see
`nginx_imagearchive.conf`. Copy the file to the nginx root after each change.

## API Endpoints

- `GET /api/images` - List all images with metadata and tags
- `GET /api/images/<image_id>` - Get single image details
- `PUT /api/images/<image_id>/description` - Update image description (login)
- `PUT|POST /api/images/<image_id>/tags` - Replace image tags (login)
- `POST /api/images/bulk/tags` - Replace tags on many images in one request (login)
- `PUT /api/images/<image_id>/reload` - Set/clear the "needs reload" flag (login)
- `PUT /api/images/<image_id>/favorite` - Add/remove a favorite for the logged-in user (login)
- `GET /api/favorites` - List the logged-in user's favorites (login)
- `POST /api/auth/login`, `POST /api/auth/logout`

## Configuration

### Image Path Mapping

The frontend converts file system paths to web URLs. By default:
- File system: `/opt/media/...`
- Web URL: `/media/...`

Update the `filePathToWebUrl()` function in `html/image_gallery.html` if your paths differ.

### API Base URL

The frontend uses the relative `API_BASE_URL` `/api/images`, so it expects nginx to proxy `/api/` to the Flask server on the same host.

## Database Schema

- **images**: Core image metadata (paths, film type, description, EXIF, reload flag, content fingerprint)
- **tags**: Unique tag names
- **image_tags**: Many-to-many relationship between images and tags
- **favorites**: Per-user favorite images

See `database_schema.sql` plus the `database_schema_exif.sql` and `add_*.sql` files.

## Development

### Re-scanning Images

After adding, editing or renaming source images:

```bash
python update_all.py
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
- Check that nginx proxies `/api/` to the API server
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

Run `update_all.py`; it only adds new images, refreshes changed ones and never touches tags,
descriptions or favorites (renamed images keep theirs). See `UPDATE_WORKFLOW.md`.

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


## URL Sharing

### Share Specific Images

When viewing an image in the modal, the URL automatically updates. You can copy this URL to share:

**Example URLs:**
```
https://yoursite.com/image_gallery.html?image=rollfilm/645_2025_Nikon/image_001
```

Anyone with this link will see that specific image opened in the modal.

### Share Searches

When searching or filtering, the URL updates with your search parameters:

**Example URLs:**
```
https://yoursite.com/image_gallery.html?search=nikon
https://yoursite.com/image_gallery.html?search=f/2.8&type=rollfilm
https://yoursite.com/image_gallery.html?search=2024-12
```

### How to Share

1. **Share an image**: Open the image → Copy browser URL → Send to someone
2. **Share a search**: Search for something → Copy browser URL → Send to someone

No "share button" needed - just copy the URL from your browser!

### Timestamp Search

You can now search by date taken:

**Search examples:**
- `2024` - All images from 2024
- `2024-12` - All images from December 2024
- `2024-12-25` - All images from Christmas Day 2024

The search includes year, month, day, and full date formats.

## Performance Optimization

`update_all.py` keeps two files in the library root:

- `.processing_index`: source/target paths with each source's mtime and size, so unchanged
  images are skipped without being re-read. Use `--force` to re-process everything.
- `.fingerprint_cache`: pixel fingerprints of the 600px versions, so rename detection only
  fingerprints new or changed images.

Both are rebuilt automatically if deleted (the first run after that is slower).
