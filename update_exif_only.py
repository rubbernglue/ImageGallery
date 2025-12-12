#!/usr/bin/env python3
"""
Update EXIF data for existing images in the database.
This script reads image_data.json and updates EXIF fields for images that already exist.
"""

import os
import sys
import json
import psycopg2

# Database configuration
DB_CONFIG = {
    'database': 'imagearchive',
    'user': 'postgres',
    'password': 'xxxxx',
    'host': 'localhost',
    'port': '5432'
}

def update_exif_data(json_file='image_data.json'):
    """
    Updates EXIF data for existing images in the database.
    """
    if not os.path.exists(json_file):
        print(f"Error: {json_file} not found.")
        return False
    
    try:
        with open(json_file, 'r') as f:
            images = json.load(f)
        
        if not images:
            print("No images found in JSON file.")
            return True
        
        conn = psycopg2.connect(**DB_CONFIG)
        
        print(f"\n=== Updating EXIF Data ===")
        print(f"Processing {len(images)} images from {json_file}")
        
        updated = 0
        skipped = 0
        errors = 0
        
        with conn:
            with conn.cursor() as cur:
                for image in images:
                    try:
                        image_id = image['image_id']
                        
                        # Check if image exists
                        cur.execute("SELECT id FROM images WHERE image_id = %s;", (image_id,))
                        existing = cur.fetchone()
                        
                        if existing:
                            # Update EXIF data
                            update_sql = """
                                UPDATE images 
                                SET camera_make = %s,
                                    camera_model = %s,
                                    lens_model = %s,
                                    focal_length = %s,
                                    aperture = %s,
                                    shutter_speed = %s,
                                    iso = %s,
                                    date_taken = %s,
                                    exif_data = %s::jsonb
                                WHERE image_id = %s;
                            """
                            
                            # Prepare EXIF data as JSON string
                            exif_json = json.dumps(image.get('exif_data', {})) if image.get('exif_data') else None
                            
                            cur.execute(update_sql, (
                                image.get('camera_make', ''),
                                image.get('camera_model', ''),
                                image.get('lens_model', ''),
                                image.get('focal_length', ''),
                                image.get('aperture', ''),
                                image.get('shutter_speed', ''),
                                image.get('iso', ''),
                                image.get('date_taken'),
                                exif_json,
                                image_id
                            ))
                            
                            # Check if any EXIF data was actually present
                            has_exif = bool(image.get('camera_model') or image.get('camera_make'))
                            
                            if cur.rowcount > 0:
                                updated += 1
                                if has_exif and updated <= 10:
                                    print(f"  ✓ Updated: {image_id} ({image.get('camera_make', '')} {image.get('camera_model', '')})")
                            else:
                                skipped += 1
                        else:
                            skipped += 1
                            
                    except Exception as e:
                        errors += 1
                        print(f"  ✗ Error updating {image.get('image_id', 'unknown')}: {e}")
        
        conn.close()
        
        print(f"\n=== Update Summary ===")
        print(f"Images updated with EXIF: {updated}")
        print(f"Images skipped (not found): {skipped}")
        print(f"Errors: {errors}")
        
        # Verify the update
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM images WHERE camera_model IS NOT NULL AND camera_model != '';")
            exif_count = cur.fetchone()[0]
            print(f"\nTotal images with EXIF in database: {exif_count}")
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Update EXIF data for existing images')
    parser.add_argument('--json', default='image_data.json', 
                        help='JSON file to read EXIF from (default: image_data.json)')
    
    args = parser.parse_args()
    
    if not update_exif_data(args.json):
        sys.exit(1)
    
    print("\n✓ EXIF update completed successfully!")
    print("\nReload your website to see EXIF data in the image modals.")

if __name__ == '__main__':
    main()
