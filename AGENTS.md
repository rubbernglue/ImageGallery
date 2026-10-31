# Agent Guidelines for ImageArchive

## Project Overview
This repository hosts a Python Flask API backend, a PostgreSQL database, and a static HTML/JavaScript frontend designed for managing a film photography archive. The application allows users to browse images, view metadata, and (for authenticated users) manage tags and descriptions.

## Running the Application

*   **API Server**: To start the Flask API, navigate to the project root and run `python api_server.py`. The server will run on `http://0.0.0.0:5000`.
*   **Library Update**: `update_all.py` resizes new/changed source images, extracts EXIF, detects renamed/orphaned images and updates the database. Run `python update_all.py --dry-run` first; see `UPDATE_WORKFLOW.md` for all options.
*   **Frontend**: The frontend is a static HTML file, `html/image_gallery.html`. No build process is required, but it uses relative URLs (`/api/...`, `/media/...`), so it must be served through nginx alongside the API (see `nginx_imagearchive.conf`).

## Build, Lint, and Test Commands

*   **Python (Backend)**:
    *   **Linting**: No specific linting tools (like `ruff` or `flake8`) are configured in the project. Adhere to the Python code style guidelines below.
    *   **Testing**: No automated tests currently exist for the Python backend. If adding tests, use `pytest`. Individual tests can be run using `pytest test_<filename>.py`. It is recommended to create a `tests/` directory for test files.
*   **Frontend (HTML/JS)**:
    *   **Linting/Building**: No build tools (like Webpack, Parcel, or Linters) are configured for the frontend. All JavaScript is vanilla and inline within `image_gallery.html`. Adhere to the JavaScript and HTML style guidelines.
    *   **Testing**: No automated tests exist for the frontend.

## Database

*   **Type**: PostgreSQL.
*   **Schema**: Defined in `database_schema.sql`. Key tables include `images`, `tags`, and `image_tags` (for many-to-many relationships).
*   **Configuration**: The database connection parameters are set in the `DB_CONFIG` dictionary within `api_server.py`. The default is `postgres/xxxxx@localhost:5432/imagearchive`. **Ensure this is updated before running in a production environment.**
*   **Library Layout**: `update_all.py` reads sources from symlinked batch folders and writes the library as `rollfilm|sheetfilm/<batch>/<image>/{600,2560}/<image>.jpg`; the database stores paths under `/opt/media` (served by nginx as `/media`).
*   **Schema Details**:
    *   `images` table: Stores core image metadata, including `image_id` (unique path string), `film_type`, `batch_info`, `filename_base`, `film_stock`, `thumbnail_path`, `highres_path`, `description`, and `created_at`/`updated_at` timestamps.
    *   `tags` table: Stores unique tag names.
    *   `image_tags` table: Junction table linking images to tags.
    *   Indices are used for performance, e.g., `idx_images_type_stock` on `images`.
    *   An `update_updated_at_column` function and trigger are in place to automatically update the `updated_at` timestamp on the `images` table.

## Code Style - Python

*   **Imports**: Follow this order, grouped with blank lines between sections:
    1.  Standard library imports (e.g., `os`, `json`, `datetime`).
    2.  Third-party library imports (e.g., `psycopg2`, `flask`, `flask_cors`).
    3.  Local application-specific imports (e.g., `config_auth`).
*   **Formatting**:
    *   Use 4-space indentation.
    *   Function names should use `snake_case` (e.g., `get_db_connection()`, `verify_password()`).
    *   Class names should use `PascalCase` (e.g., `Flask`).
    *   Constants are in `UPPER_SNAKE_CASE` (e.g., `DB_CONFIG`, `SECRET_KEY`).
*   **Types**: No explicit type hints are currently used. Maintain consistency with the existing codebase by omitting them.
*   **Error Handling**:
    *   Employ `try...except` blocks for all potentially failing operations, especially database interactions and external API calls.
    *   Print descriptive error messages to the console (e.g., `print(f"Database connection error: {e}")`).
    *   Return JSON responses with a `"success": False` flag and a user-friendly error message.
    *   Ensure database connections are properly closed in `finally` blocks to prevent resource leaks.
*   **SQL Queries**:
    *   Always use parameterized queries with `%s` placeholders for dynamic values (e.g., `SELECT id FROM images WHERE image_id = %s;`). **Never use f-strings or direct string interpolation for SQL queries to prevent SQL injection vulnerabilities.**
    *   Use `psycopg2.extras.RealDictCursor` for queries that should return results as dictionaries, making them easier to `jsonify`.
*   **Naming Conventions**:
    *   Use descriptive names for functions, variables, and parameters (e.g., `get_db_connection`, `update_tags`).
    *   Distinguish between `image_id` (the string path identifier) and `image_pk_id` (the integer primary key from the `images` table).
*   **Comments**:
    *   Add inline comments sparingly to explain complex logic or non-obvious design choices.
    *   Use docstrings for function and route handlers to explain their purpose, arguments, and return types.

## Code Style - Frontend (HTML/JavaScript)

*   **Libraries/Frameworks**:
    *   Vanilla JavaScript for all interactivity.
    *   Tailwind CSS (loaded via CDN) for styling.
    *   Leaflet.js (loaded via CDN) for map display when GPS data is available.
*   **Structure**:
    *   All JavaScript code is embedded directly within `html/image_gallery.html` inside `<script>` tags. No separate JS files are used.
    *   All CSS (except Tailwind CDN) is embedded directly within `html/image_gallery.html` inside a `<style>` tag.
*   **No Build Process**: There is no frontend build step, bundler (e.g., Webpack), or transpiler (e.g., Babel). Write modern JavaScript directly compatible with browsers.
*   **Styling**: Use Tailwind CSS classes predominantly. Custom CSS should be minimal and added to the `<style>` block in the HTML head.
*   **Interactivity**: Functions should be self-contained and clearly named (e.g., `loadData()`, `renderImageCard()`, `openModal()`).
*   **API Interaction**: Frontend interacts with the Python API via `fetch` requests. Handle API responses, including error states and success messages.
*   **URL Management**: Update browser URL parameters to reflect search and filter states.

## Authentication

*   **Mechanism**: Token-based authentication using Bearer tokens.
*   **Configuration**: User credentials (`USERS`), `SECRET_KEY`, and `TOKEN_EXPIRATION` are managed via `config_auth.py`. If `config_auth.py` is not found, default insecure values are used (WARNING).
*   **Token Persistence**: Active tokens are persisted to `/opt/api/imagearchive_tokens.json` to survive server restarts.
*   **Logging**: Authentication events (success and failure) are logged to `/var/log/imagearchive/auth.log` in a fail2ban-compatible format.
*   **Security**: Passwords are securely hashed using PBKDF2. Token verification includes expiration checks and constant-time comparison for password verification.
*   **CORS**: Flask-CORS is enabled for `/api/*` routes to allow frontend communication, with liberal `origins: *` for development (should be restricted in production).

## File System Layout / Conventions

*   The project root (`/home/johan/src/ImageArchive`) contains Python backend scripts (`api_server.py`, `database_schema.sql`).
*   The `html/` subdirectory contains the static frontend files (`image_gallery.html`).
*   Sensitive configuration is expected in `config_auth.py` (not committed).
*   Media files are expected under `/opt/media`.
