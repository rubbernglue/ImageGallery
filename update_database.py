#!/usr/bin/env python3
"""
Incremental database update script for ImageArchive.
Only adds new images without rewriting the entire database.
"""

import os
import sys
import json
import psycopg2

# Database configuration - update these to match your PostgreSQL setup
DB_CONFIG = {
    'database': 'imagearchive',
    'user': 'postgres',
    'password': 'xxxxx',
    'host': 'localhost',
    'port': '5432'
}

def update_database_from_json(json_file='image_data.json'):
    """
    Updates the database with new images from JSON file.
    Only inserts new images, skips existing ones.
    """
    if not os.path.exists(json_file):
        print(f"Error: {json_file} not found.")
        print("Run 'python library_scanner.py' first to generate the JSON file.")
        return False
    
    try:
        with open(json_file, 'r') as f:
            images = json.load(f)
        
        if not images:
            print("No images found in JSON file.")
            return True
        
        conn = psycopg2.connect(**DB_CONFIG)
        
        print(f"\n=== Incremental Database Update ===")
        print(f"Processing {len(images)} images from {json_file}")
        
        inserted = 0
        updated = 0
        skipped = 0
        errors = 0
        
        with conn:
            with conn.cursor() as cur:
                for image in images:
                    try:
                        image_id = image['image_id']
                        
                        # Check if image already exists
                        cur.execute("SELECT id, description FROM images WHERE image_id = %s;", (image_id,))
                        existing = cur.fetchone()
                        
                        if existing:
                            # Image exists - optionally update paths if they changed
                            existing_id = existing[0]
                            existing_desc = existing[1]
                            
                            # Only update if paths have changed
                            cur.execute("""
                                UPDATE images 
                                SET thumbnail_path = %s, highres_path = %s
                                WHERE image_id = %s 
                                AND (thumbnail_path != %s OR highres_path != %s);
                            """, (
                                image['thumbnail_path'], 
                                image['highres_path'],
                                image_id,
                                image['thumbnail_path'],
                                image['highres_path']
                            ))
                            
                            if cur.rowcount > 0:
                                updated += 1
                                print(f"  Updated paths: {image_id}")
                            else:
                                skipped += 1
                        else:
                            # New image - insert it with EXIF data
                            insert_sql = """
                                INSERT INTO images 
                                (image_id, film_type, batch_info, filename_base, film_stock, 
                                 thumbnail_path, highres_path, description,
                                 camera_make, camera_model, lens_model, focal_length,
                                 aperture, shutter_speed, iso, date_taken, exif_data)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                            """
                            
                            # Prepare EXIF data as JSON string
                            exif_json = json.dumps(image.get('exif_data', {})) if image.get('exif_data') else None
                            
                            cur.execute(insert_sql, (
                                image['image_id'],
                                image['film_type'],
                                image['batch_info'],
                                image['filename_base'],
                                image['film_stock'],
                                image['thumbnail_path'],
                                image['highres_path'],
                                image.get('description', ''),
                                image.get('camera_make', ''),
                                image.get('camera_model', ''),
                                image.get('lens_model', ''),
                                image.get('focal_length', ''),
                                image.get('aperture', ''),
                                image.get('shutter_speed', ''),
                                image.get('iso', ''),
                                image.get('date_taken'),
                                exif_json
                            ))
                            inserted += 1
                            print(f"  Inserted: {image_id}")
                            
                    except Exception as e:
                        errors += 1
                        print(f"  Error processing {image.get('image_id', 'unknown')}: {e}")
        
        conn.close()
        
        print(f"\n=== Update Summary ===")
        print(f"New images inserted: {inserted}")
        print(f"Existing images updated: {updated}")
        print(f"Unchanged images skipped: {skipped}")
        print(f"Errors: {errors}")
        
        return True
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def scan_specific_directory(base_dir, subdirectory):
    """
    Scan only a specific subdirectory and update the database.
    Example: scan_specific_directory('/opt/media/rollfilm', '645_2025_Nikon_med_Ilford')
    """
    import re
    from library_scanner import parse_path
    
    full_path = os.path.join(base_dir, subdirectory)
    
    if not os.path.isdir(full_path):
        print(f"Error: Directory not found: {full_path}")
        return False
    
    print(f"\n=== Scanning Subdirectory: {subdirectory} ===")
    
    images = {}
    count = 0
    
    for root, dirs, files in os.walk(full_path):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg')):
                full_file_path = os.path.join(root, file)
                normalized_path = full_file_path.replace('\\', os.sep)
                
                image_id, data = parse_path(normalized_path, base_dir)
                
                if image_id:
                    if image_id not in images:
                        images[image_id] = {
                            'image_id': image_id,
                            'film_type': data['film_type'],
                            'batch_info': data['batch_info'],
                            'filename_base': data['filename_base'],
                            'film_stock': data['film_stock'],
                            'thumbnail_path': None,
                            'highres_path': None,
                            'description': '',
                        }
                    
                    if data['resolution'] == '600':
                        images[image_id]['thumbnail_path'] = full_file_path
                    elif data['resolution'] == '2560':
                        images[image_id]['highres_path'] = full_file_path
                    
                    count += 1
    
    final_images = [img for img in images.values() if img['thumbnail_path'] and img['highres_path']]
    print(f"Found {len(final_images)} complete image pairs in subdirectory")
    
    if not final_images:
        print("No complete image pairs found (need both 600px and 2560px versions)")
        return False
    
    # Save to temporary JSON and update database
    temp_json = f"temp_{subdirectory.replace('/', '_')}.json"
    with open(temp_json, 'w') as f:
        json.dump(final_images, f, indent=4)
    
    print(f"Saved temporary data to {temp_json}")
    result = update_database_from_json(temp_json)
    
    # Clean up temp file
    if os.path.exists(temp_json):
        os.remove(temp_json)
    
    return result

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Incremental database update for ImageArchive')
    parser.add_argument('--json', default='image_data.json', 
                        help='JSON file to import (default: image_data.json)')
    parser.add_argument('--scan-dir', nargs=2, metavar=('BASE_DIR', 'SUBDIR'),
                        help='Scan specific subdirectory (e.g., /opt/media/rollfilm 645_2025_Nikon_med_Ilford)')
    
    args = parser.parse_args()
    
    if args.scan_dir:
        base_dir, subdir = args.scan_dir
        if not scan_specific_directory(base_dir, subdir):
            sys.exit(1)
    else:
        if not update_database_from_json(args.json):
            sys.exit(1)
    
    print("\n✓ Database update completed successfully!")
    print("Run 'python api_server.py' to start the API server if not already running.")

if __name__ == '__main__':
    main()
