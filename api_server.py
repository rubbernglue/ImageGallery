import os
import json
import psycopg2
import psycopg2.extras # REQUIRED for RealDictCursor
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- IMPORTANT: CONFIGURE YOUR DATABASE CONNECTION HERE ---
DB_CONFIG = {
    'database': 'imagearchive',
    'user': 'postgres',
    'password': 'xxxxx',
    'host': 'localhost', # Or the IP of your PostgreSQL server
    'port': '5432'
}
# ---------------------------------------------------------

app = Flask(__name__)
# Enable CORS for the frontend to communicate with this API
CORS(app) 

def get_db_connection():
    """Establishes and returns a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

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
                    i.date,
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
                    i.id, i.image_id, i.description, i.date, i.highres_path;
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
def update_tags(image_id):
    """
    Replaces all existing tags for a specific image_id (the path string) with a new list of tags.
    This route now accepts both PUT and POST methods.
    """
    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "message": "Database unavailable"}), 503

    image_pk_id = None # Initialize to handle error logging
    try:
        data = request.get_json()
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
@app.route('/api/images/<path:image_id>/description', methods=['PUT'])
def update_description(image_id):
    """Updates the description field for a specific image_id."""
    # ... your existing update_description code here ...
    pass
    
@app.route('/api/images/<path:image_id>/tag', methods=['POST'])
def add_tag(image_id):
    """Simulates adding a tag. Keeping this route separate for now."""
    data = request.get_json()
    new_tag = data.get('tag', '').strip()
    
    if not new_tag:
        return jsonify({"success": False, "message": "Tag missing"}), 400

    # This route should likely be removed if 'update_tags' is used for all tag modification.
    print(f"Simulated POST to DB: Adding tag '{new_tag}' to image '{image_id}'")
    
    return jsonify({"success": True, "message": f"Tag '{new_tag}' added (simulated). You need to implement the database logic."}), 200


if __name__ == '__main__':
    # Run the server on port 5000
    print("Starting Flask API server on http://0.0.0.0:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
