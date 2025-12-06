# Agent Guidelines for ImageArchive

## Project Overview
Python Flask API backend + PostgreSQL database + HTML/JS frontend for managing a film photography archive.

## Running the Application
- **API Server**: `python api_server.py` (runs on http://0.0.0.0:5000)
- **Library Scanner**: `python library_scanner.py` (generates image_data.json and image_inserts.sql)
- **Frontend**: Open `image_gallery.html` in a browser (static file, no build needed)
- **No tests exist yet** - if adding tests, use `pytest` and run with `pytest test_<filename>.py`

## Database
- PostgreSQL (see `database_schema.sql` for schema)
- Update DB_CONFIG in `api_server.py` before running (default: postgres/xxxxx@localhost:5432/imagearchive)
- Scanner expects `/opt/media` with `rollfilm/` and `sheetfilm/` subdirectories

## Code Style - Python
- **Imports**: Standard library first, then third-party (psycopg2, Flask), then local. Group with blank lines
- **Formatting**: 4-space indentation, functions use snake_case, classes use PascalCase
- **Types**: No type hints used currently - keep consistent with existing code
- **Error Handling**: Try/except with connection cleanup in finally blocks. Print errors, return JSON with success flag
- **SQL**: Use parameterized queries with %s placeholders (never string interpolation for security)
- **Naming**: Descriptive function names like `get_db_connection()`, `update_tags()`. Use `image_id` for path strings, `image_pk_id` for integer IDs
- **Comments**: Inline for complex logic, docstrings for route handlers explaining purpose and return types

## Code Style - Frontend
- Vanilla JavaScript with Tailwind CSS (loaded via CDN)
- No build process or bundler
- Keep all JS inline in the HTML file for simplicity
