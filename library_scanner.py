import os
import re
import json
from PIL import Image
from PIL.ExifTags import TAGS
from PIL.TiffImagePlugin import IFDRational
from datetime import datetime
from fractions import Fraction

class ExifEncoder(json.JSONEncoder):
    """Custom JSON encoder for EXIF data types."""
    def default(self, o):
        if isinstance(o, IFDRational):
            return float(o)
        elif isinstance(o, bytes):
            try:
                return o.decode('utf-8', errors='ignore')
            except:
                return str(o)
        elif isinstance(o, Fraction):
            return float(o)
        # Let the base class raise TypeError for other non-serializable types
        return super().default(o)

# IMPORTANT: SET THIS TO YOUR ACTUAL ROOT DIRECTORY CONTAINING 'rollfilm' and 'sheetfilm'
# Based on your console output, we'll use /opt/media as a placeholder.
# If your structure is /opt/media/Picture_library/, you must set BASE_DIR to '/opt/media/Picture_library'.
BASE_DIR = '/opt/media' 

# Define the expected root folders to simplify parsing
ROOT_FILM_TYPES = ['rollfilm', 'sheetfilm']

def convert_to_serializable(obj):
    """Convert EXIF values to JSON-serializable types."""
    if isinstance(obj, IFDRational):
        # Convert IFDRational to float
        return float(obj)
    elif isinstance(obj, bytes):
        # Convert bytes to string
        try:
            return obj.decode('utf-8', errors='ignore')
        except:
            return str(obj)
    elif isinstance(obj, (list, tuple)):
        # Recursively convert lists/tuples
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        # Recursively convert dictionaries
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif hasattr(obj, '__dict__'):
        # Convert objects with __dict__ to their dict representation
        return convert_to_serializable(obj.__dict__)
    else:
        # Return as-is if already serializable
        return obj

def format_focal_length(focal_length):
    """Format focal length nicely (e.g., '50mm' or '24-70mm')."""
    if not focal_length:
        return ''
    try:
        if isinstance(focal_length, (IFDRational, Fraction)):
            focal_length = float(focal_length)
        if isinstance(focal_length, (int, float)):
            return f"{int(focal_length)}mm"
        return str(focal_length)
    except:
        return str(focal_length)

def format_aperture(f_number):
    """Format aperture nicely (e.g., 'f/2.8')."""
    if not f_number:
        return ''
    try:
        if isinstance(f_number, (IFDRational, Fraction)):
            f_number = float(f_number)
        if isinstance(f_number, (int, float)):
            return f"f/{f_number:.1f}"
        return f"f/{f_number}"
    except:
        return str(f_number)

def format_shutter_speed(exposure_time):
    """Format shutter speed nicely (e.g., '1/1000' or '2s')."""
    if not exposure_time:
        return ''
    try:
        if isinstance(exposure_time, (IFDRational, Fraction)):
            exposure_time = float(exposure_time)
        if isinstance(exposure_time, (int, float)):
            if exposure_time < 1:
                # Fast shutter speed - show as fraction
                return f"1/{int(1/exposure_time)}"
            else:
                # Slow shutter speed - show in seconds
                return f"{exposure_time}s"
        return str(exposure_time)
    except:
        return str(exposure_time)

def extract_exif(image_path):
    """Extract EXIF data from an image file."""
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        
        if not exif_data:
            return None
        
        # Convert EXIF tags to readable names and make serializable
        exif = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            # Convert to serializable format immediately
            exif[tag] = convert_to_serializable(value)
        
        # Extract and format commonly needed fields
        result = {
            'camera_make': str(exif.get('Make', '')).strip() if exif.get('Make') else '',
            'camera_model': str(exif.get('Model', '')).strip() if exif.get('Model') else '',
            'lens_model': str(exif.get('LensModel', '')).strip() if exif.get('LensModel') else '',
            'focal_length': format_focal_length(exif.get('FocalLength')),
            'aperture': format_aperture(exif.get('FNumber')),
            'shutter_speed': format_shutter_speed(exif.get('ExposureTime')),
            'iso': str(exif.get('ISOSpeedRatings', '')) if exif.get('ISOSpeedRatings') else '',
            'date_taken': None,
            'exif_data': exif  # Store full EXIF (now serializable)
        }
        
        # Parse date taken
        date_str = exif.get('DateTimeOriginal') or exif.get('DateTime')
        if date_str:
            try:
                result['date_taken'] = datetime.strptime(str(date_str), '%Y:%m:%d %H:%M:%S').isoformat()
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
                            # Make sure all EXIF values are serializable strings/numbers
                            images[image_id].update({
                                'camera_make': str(exif.get('camera_make', '')),
                                'camera_model': str(exif.get('camera_model', '')),
                                'lens_model': str(exif.get('lens_model', '')),
                                'focal_length': str(exif.get('focal_length', '')),
                                'aperture': str(exif.get('aperture', '')),
                                'shutter_speed': str(exif.get('shutter_speed', '')),
                                'iso': str(exif.get('iso', '')),
                                'date_taken': exif.get('date_taken', ''),
                                'exif_data': exif.get('full_exif', {})  # Already converted to serializable
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
        
        # Make all data JSON-serializable before dumping
        print(f"\nPreparing data for JSON export...")
        serializable_list = []
        errors = 0
        
        for img in image_list:
            try:
                # Convert the entire image dict to serializable format
                serializable_img = convert_to_serializable(img)
                serializable_list.append(serializable_img)
            except Exception as e:
                print(f"  Error serializing {img.get('image_id', 'unknown')}: {e}")
                errors += 1
        
        if errors > 0:
            print(f"  Warning: {errors} images had serialization issues")
        
        try:
            with open(json_output_path, 'w') as f:
                json.dump(serializable_list, f, indent=4, cls=ExifEncoder, default=str)
            print(f"Successfully generated {json_output_path}")
        except Exception as e:
            print(f"Error writing JSON: {e}")
            print("Attempting to write with basic serialization...")
            # Fallback - write without EXIF data
            basic_list = [{k: v for k, v in img.items() if k != 'exif_data'} for img in serializable_list]
            with open(json_output_path, 'w') as f:
                json.dump(basic_list, f, indent=4, default=str)
            print(f"Successfully generated {json_output_path} (without full EXIF data)")

        # 3. Output data to SQL (for PostgreSQL)
        sql_output_path = 'image_inserts.sql'
        sql_content = generate_sql_inserts(image_list)
        with open(sql_output_path, 'w') as f:
            f.write(sql_content)
        print(f"Successfully generated {sql_output_path}")

        print("\n--- Important Next Step ---")
        print(f"Make sure {BASE_DIR} is the path containing your 'rollfilm' and 'sheetfilm' folders. If not, edit the BASE_DIR variable at the top of this script.")
