import os
import re
import json
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime

# IMPORTANT: SET THIS TO YOUR ACTUAL ROOT DIRECTORY CONTAINING 'rollfilm' and 'sheetfilm'
# Based on your console output, we'll use /opt/media as a placeholder.
# If your structure is /opt/media/Picture_library/, you must set BASE_DIR to '/opt/media/Picture_library'.
BASE_DIR = '/opt/media' 

# Define the expected root folders to simplify parsing
ROOT_FILM_TYPES = ['rollfilm', 'sheetfilm']

def extract_exif(image_path):
    """Extract EXIF data from an image file."""
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        
        if not exif_data:
            return None
        
        # Convert EXIF tags to readable names
        exif = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            exif[tag] = value
        
        # Extract commonly needed fields
        result = {
            'camera_make': exif.get('Make', '').strip(),
            'camera_model': exif.get('Model', '').strip(),
            'lens_model': exif.get('LensModel', '').strip(),
            'focal_length': str(exif.get('FocalLength', '')),
            'aperture': f"f/{exif.get('FNumber', '')}" if exif.get('FNumber') else '',
            'shutter_speed': str(exif.get('ExposureTime', '')),
            'iso': str(exif.get('ISOSpeedRatings', '')),
            'date_taken': None,
            'full_exif': exif  # Store full EXIF for advanced use
        }
        
        # Parse date taken
        date_str = exif.get('DateTimeOriginal') or exif.get('DateTime')
        if date_str:
            try:
                result['date_taken'] = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S').isoformat()
            except:
                pass
        
        return result
    except Exception as e:
        print(f"  Warning: Could not extract EXIF from {image_path}: {e}")
        return None

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
                        # Extract EXIF from high-res image
                        print(f"  Extracting EXIF from: {image_id}")
                        exif = extract_exif(full_path)
                        if exif:
                            images[image_id].update({
                                'camera_make': exif.get('camera_make', ''),
                                'camera_model': exif.get('camera_model', ''),
                                'lens_model': exif.get('lens_model', ''),
                                'focal_length': exif.get('focal_length', ''),
                                'aperture': exif.get('aperture', ''),
                                'shutter_speed': exif.get('shutter_speed', ''),
                                'iso': exif.get('iso', ''),
                                'date_taken': exif.get('date_taken', ''),
                                'exif_data': exif.get('full_exif', {})
                            })

    # Convert the dictionary of images to a list, ensuring both paths were found
    final_data = [img for img in images.values() if img['thumbnail_path'] and img['highres_path']]
    print(f"Found {len(final_data)} unique image pairs (600px and 2560px).")
    print(f"Extracted EXIF data from {sum(1 for img in final_data if img.get('camera_model'))} images.")
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
