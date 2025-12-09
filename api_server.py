import os
import json
import secrets
import hashlib
import hmac
import time
import psycopg2
import psycopg2.extras # REQUIRED for RealDictCursor
from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps

# --- IMPORTANT: CONFIGURE YOUR DATABASE CONNECTION HERE ---
DB_CONFIG = {
    'database': 'imagearchive',
    'user': 'postgres',
    'password': 'xxxxx',
    'host': 'localhost', # Or the IP of your PostgreSQL server
    'port': '5432'
}

# Secret key for password hashing - CHANGE THIS TO A RANDOM VALUE!
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = 'change_this_to_a_random_secret_key_generated_above'

# ============================================================================
# User credentials with salted hashed passwords
# ============================================================================
# To add a new user:
# 1. Run: python generate_password_hash.py
# 2. Enter username and password when prompted
# 3. Copy the entire dictionary entry (including the username line)
# 4. Paste it into the USERS dictionary below
#
# EXAMPLE OUTPUT from generate_password_hash.py:
#     'myusername': {
#         'salt': 'a1b2c3d4e5f6...',
#         'hash': '1234567890abcdef...'
#     },
#
# The script generates both the salt AND the hash for you!
# Just copy-paste the entire block including the username.
# ============================================================================

USERS = {
    # Default admin user - password: 'admin123' - CHANGE THIS!
    'admin': {
        'salt': '8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d',
        'hash': hashlib.pbkdf2_hmac('sha256', b'admin123', b'8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d', 100000).hex()
    },
    # Add more users below by running: python generate_password_hash.py
    # Then copy-paste the output here:
    
}

# Store active tokens with expiration (in production, use database or Redis)
active_tokens = {}  # Format: {token: {'username': username, 'expires': timestamp}}

# Token expiration time in seconds (24 hours)
TOKEN_EXPIRATION = 86400

# ---------------------------------------------------------

def verify_password(username, password):
    """Securely verify password using PBKDF2."""
    if username not in USERS:
        return False
    
    user_data = USERS[username]
    salt = user_data['salt'].encode()
    stored_hash = user_data['hash']
    
    # Hash the provided password with the same salt
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000).hex()
    
    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(password_hash, stored_hash)

def clean_expired_tokens():
    """Remove expired tokens from memory."""
    current_time = time.time()
    expired = [token for token, data in active_tokens.items() 
               if data['expires'] < current_time]
    for token in expired:
        del active_tokens[token]

app = Flask(__name__)
# Enable CORS for the frontend to communicate with this API
# Allow all origins and methods for development (restrict in production!)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type"],
        "supports_credentials": False
    }
}) 

def get_db_connection():
    """Establishes and returns a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def require_auth(f):
    """Decorator to require authentication for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"success": False, "message": "Authentication required"}), 401
        
        token = auth_header.split(' ')[1]
        
        # Check if token exists and is not expired
        if token not in active_tokens:
            return jsonify({"success": False, "message": "Invalid or expired token"}), 401
        
        token_data = active_tokens[token]
        if token_data['expires'] < time.time():
            # Token expired, remove it
            del active_tokens[token]
            return jsonify({"success": False, "message": "Token expired, please log in again"}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

# =======================================================================
# AUTHENTICATION ENDPOINTS
# =======================================================================
@app.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate user and return token."""
    try:
        # Clean up expired tokens before processing login
        clean_expired_tokens()
        
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"success": False, "message": "Username and password required"}), 400
        
        # Verify credentials using secure password verification
        if verify_password(username, password):
            # Generate secure token
            token = secrets.token_urlsafe(32)
            
            # Store token with expiration time
            active_tokens[token] = {
                'username': username,
                'expires': time.time() + TOKEN_EXPIRATION
            }
            
            print(f"[AUTH] User '{username}' logged in successfully (token expires in {TOKEN_EXPIRATION/3600:.1f} hours)")
            return jsonify({
                "success": True, 
                "token": token, 
                "username": username,
                "expires_in": TOKEN_EXPIRATION
            }), 200
        else:
            print(f"[AUTH] Failed login attempt for username: {username}")
            return jsonify({"success": False, "message": "Invalid credentials"}), 401
            
    except Exception as e:
        print(f"[ERROR] Login error: {e}")
        return jsonify({"success": False, "message": "Internal server error"}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout user and invalidate token."""
    try:
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            if token in active_tokens:
                username = active_tokens[token]['username']
                del active_tokens[token]
                print(f"[AUTH] User '{username}' logged out")
        
        return jsonify({"success": True, "message": "Logged out successfully"}), 200
    except Exception as e:
        print(f"[ERROR] Logout error: {e}")
        return jsonify({"success": False, "message": "Internal server error"}), 500

# =======================================================================
# 1. READ/GET ENDPOINT (Fixes tags disappearing on reload)
# =======================================================================
@app.route('/api/images/<path:image_id>', methods=['GET'])
def get_image_details(image_id):
    """
    Retrieves a single image's details, including the description and aggregated tags, 
    using the image_id (the file path string).
    """
    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    try:
        # Use RealDictCursor to return results as dictionaries (easier for jsonify)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # SQL query uses JOIN and array_agg to retrieve all tags in a single field
            sql_query = """
                SELECT
                    i.image_id,
                    i.description,
                    i.highres_path AS path, -- Assuming the frontend expects 'path' to be the high-res path
                    COALESCE(array_agg(t.name) FILTER (WHERE t.name IS NOT NULL), '{}') AS tags
                FROM 
                    images i
                LEFT JOIN 
                    image_tags it ON i.id = it.image_id
                LEFT JOIN 
                    tags t ON it.tag_id = t.id
                WHERE 
                    i.image_id = %s
                GROUP BY 
                    i.id, i.image_id, i.description, i.highres_path;
            """
            cur.execute(sql_query, (image_id,))
            image_details = cur.fetchone()

            if not image_details:
                return jsonify({"success": False, "message": f"Image '{image_id}' not found."}), 404
            
            # The PostgreSQL array_agg result is automatically handled by psycopg2, 
            # but we ensure the dictionary structure is clean.
            
            return jsonify({"success": True, "image": image_details}), 200

    except Exception as e:
        print(f"Error fetching image details for {image_id}: {e}")
        return jsonify({"success": False, "message": "Internal server error during data retrieval"}), 500
    finally:
        if conn:
            conn.close()


# =======================================================================
# 2. WRITE/PUT/POST ENDPOINT (Fixes 405 Method Not Allowed)
# =======================================================================
@app.route('/api/images/<path:image_id>/tags', methods=['PUT', 'POST'])
@require_auth
def update_tags(image_id):
    """
    Replaces all existing tags for a specific image_id (the path string) with a new list of tags.
    This route now accepts both PUT and POST methods.
    """
    print(f"[DEBUG] update_tags called with image_id: {image_id}, method: {request.method}")
    
    conn = get_db_connection()
    if not conn:
        print(f"[ERROR] Database connection failed for update_tags")
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    image_pk_id = None # Initialize to handle error logging
    try:
        data = request.get_json()
        print(f"[DEBUG] Received data: {data}")
        new_tags = data.get('tags', [])
        
        if not isinstance(new_tags, list):
            return jsonify({"success": False, "message": "Tags must be a list"}), 400

        cleaned_tags = [tag.strip().lower() for tag in new_tags if tag.strip()]

        with conn:
            with conn.cursor() as cur:
                
                # STEP 1: Get the INTEGER primary key (images.id) from the string path (image_id)
                cur.execute("SELECT id FROM images WHERE image_id = %s;", (image_id,))
                image_db_row = cur.fetchone()
                
                if not image_db_row:
                    return jsonify({"success": False, "message": f"Image path '{image_id}' not found in the database."}), 404
                
                image_pk_id = image_db_row[0]

                # STEP 2: Delete all existing tags for this image using the INTEGER ID
                cur.execute("DELETE FROM image_tags WHERE image_id = %s;", (image_pk_id,))

                for tag_name in set(cleaned_tags):
                    # STEP 3: Upsert the tag name into the 'tags' table
                    sql_tag_upsert = """
                        INSERT INTO tags (name)
                        VALUES (%s) 
                        ON CONFLICT (name) DO UPDATE 
                        SET name = EXCLUDED.name 
                        RETURNING id;
                    """
                    cur.execute(sql_tag_upsert, (tag_name,))
                    tag_id = cur.fetchone()[0]

                    # STEP 4: Link the image and the tag in the image_tags table
                    sql_link = "INSERT INTO image_tags (image_id, tag_id) VALUES (%s, %s);"
                    cur.execute(sql_link, (image_pk_id, tag_id))
        
        print(f"[SUCCESS] Tags updated for image_id={image_id}, count={len(cleaned_tags)}")
        return jsonify({"success": True, "message": f"Tags updated successfully. {len(cleaned_tags)} tags applied."}), 200

    except Exception as e:
        print(f"Error executing tag update for {image_id} (Internal ID: {image_pk_id if image_pk_id else 'N/A'}): {e}")
        return jsonify({"success": False, "message": "Internal server error during tag update"}), 500
    finally:
        if conn:
            conn.close()

# =======================================================================
# OTHER ROUTES
# =======================================================================
@app.route('/api/images', methods=['GET'])
def list_images():
    """
    Retrieves all images with their metadata including tags.
    Returns a JSON array of all images in the database.
    """
    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            sql_query = """
                SELECT
                    i.image_id,
                    i.film_type,
                    i.batch_info,
                    i.filename_base,
                    i.film_stock,
                    i.thumbnail_path,
                    i.highres_path,
                    i.description,
                    i.camera_make,
                    i.camera_model,
                    i.lens_model,
                    i.focal_length,
                    i.aperture,
                    i.shutter_speed,
                    i.iso,
                    i.date_taken,
                    COALESCE(array_agg(t.name) FILTER (WHERE t.name IS NOT NULL), '{}') AS tags
                FROM 
                    images i
                LEFT JOIN 
                    image_tags it ON i.id = it.image_id
                LEFT JOIN 
                    tags t ON it.tag_id = t.id
                GROUP BY 
                    i.id, i.image_id, i.film_type, i.batch_info, i.filename_base, 
                    i.film_stock, i.thumbnail_path, i.highres_path, i.description,
                    i.camera_make, i.camera_model, i.lens_model, i.focal_length,
                    i.aperture, i.shutter_speed, i.iso, i.date_taken
                ORDER BY i.id;
            """
            cur.execute(sql_query)
            images = cur.fetchall()
            
            return jsonify({"success": True, "images": images, "count": len(images)}), 200

    except Exception as e:
        print(f"Error fetching images list: {e}")
        return jsonify({"success": False, "message": "Internal server error during data retrieval"}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/images/<path:image_id>/description', methods=['PUT'])
@require_auth
def update_description(image_id):
    """Updates the description field for a specific image_id."""
    print(f"[DEBUG] update_description called with image_id: {image_id}")
    
    conn = get_db_connection()
    if not conn:
        print(f"[ERROR] Database connection failed for update_description")
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    try:
        data = request.get_json()
        print(f"[DEBUG] Received data: {data}")
        new_description = data.get('description', '').strip()
        
        with conn:
            with conn.cursor() as cur:
                # Check if image exists
                cur.execute("SELECT id FROM images WHERE image_id = %s;", (image_id,))
                image_db_row = cur.fetchone()
                
                if not image_db_row:
                    return jsonify({"success": False, "message": f"Image path '{image_id}' not found in the database."}), 404
                
                # Update description
                cur.execute(
                    "UPDATE images SET description = %s WHERE image_id = %s;",
                    (new_description, image_id)
                )
        
        print(f"[SUCCESS] Description updated for image_id={image_id}")
        return jsonify({"success": True, "message": "Description updated successfully."}), 200

    except Exception as e:
        print(f"Error updating description for {image_id}: {e}")
        return jsonify({"success": False, "message": "Internal server error during description update"}), 500
    finally:
        if conn:
            conn.close()



if __name__ == '__main__':
    # Run the server on port 5000
    print("Starting Flask API server on http://0.0.0.0:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
