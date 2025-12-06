import os
import re
import json

# IMPORTANT: SET THIS TO YOUR ACTUAL ROOT DIRECTORY CONTAINING 'rollfilm' and 'sheetfilm'
# Based on your console output, we'll use /opt/media as a placeholder.
# If your structure is /opt/media/Picture_library/, you must set BASE_DIR to '/opt/media/Picture_library'.
BASE_DIR = '/opt/media' 

# Define the expected root folders to simplify parsing
ROOT_FILM_TYPES = ['rollfilm', 'sheetfilm']

def parse_path(full_path, base_dir):
    """
    Parses a path relative to the base directory to extract structured metadata.
    This function is now robust against absolute paths.
    """
    # 1. Get the path relative to the BASE_DIR
    relative_path = os.path.relpath(full_path, base_dir)
    parts = relative_path.split(os.sep)
    
    # Expected structure of the relative path components:
    # 0: film_type (e.g., 'sheetfilm', 'rollfilm')
    # 1: batch_info (e.g., '5x7_0041-0045' or '482_2020_Bronica...')
    # 2: filename_base (e.g., '0042_Panchro400' or 'ilford125_08')
    # 3: resolution (e.g., '600', '2560')
    # 4: filename.jpg

    # Ensure the path has the minimum required depth and starts with a known film type
    if len(parts) < 5 or parts[0] not in ROOT_FILM_TYPES:
        return None, None

    film_type = parts[0]
    batch_info = parts[1]
    filename_base = parts[2]
    resolution = parts[3]
    
    # Extract film stock from the filename_base (assuming it's at the end, e.g., Panchro400)
    match = re.search(r'(_)?([a-zA-Z]+[0-9]+)$', filename_base)
    film_stock = match.group(2) if match else "Unknown"
    
    # The unique key for the image should be independent of resolution
    # We use a relative path structure for the ID
    image_id = f"{film_type}/{batch_info}/{filename_base}"
    
    return image_id, {
        'image_id': image_id,
        'film_type': film_type,
        'batch_info': batch_info,
        'filename_base': filename_base,
        'film_stock': film_stock,
        'resolution': resolution,
        'full_path': full_path # Keep the absolute path for reference
    }

def scan_library(base_dir):
    """Scans the directory structure and collates image data."""
    print(f"Scanning directory: {base_dir}")
    images = {}
    
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg')):
                full_path = os.path.join(root, file)
                # Normalize path for consistent parsing
                normalized_path = full_path.replace('\\', os.sep) 
                
                image_id, data = parse_path(normalized_path, base_dir)
                
                if image_id:
                    if image_id not in images:
                        # Initialize unique image record
                        images[image_id] = {
                            'image_id': image_id,
                            'film_type': data['film_type'],
                            'batch_info': data['batch_info'],
                            'filename_base': data['filename_base'],
                            'film_stock': data['film_stock'],
                            'thumbnail_path': None,
                            'highres_path': None,
                            'description': '', # Placeholder for database field
                        }
                    
                    # Assign the specific resolution path
                    if data['resolution'] == '600':
                        images[image_id]['thumbnail_path'] = full_path
                    elif data['resolution'] == '2560':
                        images[image_id]['highres_path'] = full_path

    # Convert the dictionary of images to a list, ensuring both paths were found
    final_data = [img for img in images.values() if img['thumbnail_path'] and img['highres_path']]
    print(f"Found {len(final_data)} unique image pairs (600px and 2560px).")
    return final_data

def generate_sql_inserts(data):
    """Generates PostgreSQL INSERT statements."""
    sql_statements = ["-- SQL Insert Statements Generated from library_scanner.py\n"]
    
    for item in data:
        # Escape single quotes in strings for SQL
        description = item['description'].replace("'", "''") 
        
        insert_sql = (
            f"INSERT INTO images (image_id, film_type, batch_info, filename_base, film_stock, thumbnail_path, highres_path, description) "
            f"VALUES ('{item['image_id']}', '{item['film_type']}', '{item['batch_info']}', '{item['filename_base']}', '{item['film_stock']}', '{item['thumbnail_path']}', '{item['highres_path']}', '{description}');"
        )
        sql_statements.append(insert_sql)
        
    return "\n".join(sql_statements)

if __name__ == '__main__':
    # Ensure BASE_DIR exists
    if not os.path.isdir(BASE_DIR):
        print(f"Error: Base directory '{BASE_DIR}' not found. Please update the BASE_DIR variable.")
    else:
        # 1. Scan the library
        image_list = scan_library(BASE_DIR)

        # 2. Output data to JSON (for frontend demo/testing)
        json_output_path = 'image_data.json'
        with open(json_output_path, 'w') as f:
            json.dump(image_list, f, indent=4)
        print(f"\nSuccessfully generated {json_output_path}")

        # 3. Output data to SQL (for PostgreSQL)
        sql_output_path = 'image_inserts.sql'
        sql_content = generate_sql_inserts(image_list)
        with open(sql_output_path, 'w') as f:
            f.write(sql_content)
        print(f"Successfully generated {sql_output_path}")

        print("\n--- Important Next Step ---")
        print(f"Make sure {BASE_DIR} is the path containing your 'rollfilm' and 'sheetfilm' folders. If not, edit the BASE_DIR variable at the top of this script.")
