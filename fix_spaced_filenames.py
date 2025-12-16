#!/usr/bin/env python3
"""
Fix database entries that have spaces in filenames.
Replace with underscore versions that actually exist on disk.
"""

import os
import psycopg2

DB_CONFIG = {
    'database': 'imagearchive',
    'user': 'postgres',
    'password': 'xxxxx',
    'host': '172.16.8.26',
    'port': '5432'
}

PATH_DATABASE = "/opt/media"

def fix_spaced_filenames():
    """Update database paths to use underscored filenames."""
    
    print("=" * 70)
    print("Fix Spaced Filenames in Database")
    print("=" * 70)
    print()
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        # Find all images with spaces in their paths
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, image_id, thumbnail_path, highres_path 
                FROM images 
                WHERE thumbnail_path LIKE '% %' 
                   OR highres_path LIKE '% %'
                   OR image_id LIKE '% %';
            """)
            images_with_spaces = cur.fetchall()
        
        if not images_with_spaces:
            print("✓ No images with spaces in filenames")
            print("  Database is clean!")
            conn.close()
            return True
        
        print(f"Found {len(images_with_spaces)} images with spaces in filenames\n")
        
        fixed = 0
        skipped = 0
        errors = 0
        
        for img_id, image_id, thumb_path, highres_path in images_with_spaces:
            try:
                # Replace spaces with underscores
                new_image_id = image_id.replace(' ', '_')
                new_thumb = thumb_path.replace(' ', '_') if thumb_path else None
                new_highres = highres_path.replace(' ', '_') if highres_path else None
                
                # Check if underscored version already exists in database
                with conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT id FROM images WHERE image_id = %s;", (new_image_id,))
                        duplicate = cur.fetchone()
                        
                        if duplicate:
                            # Underscored version exists - delete the spaced entry
                            cur.execute("DELETE FROM image_tags WHERE image_id = %s;", (img_id,))
                            cur.execute("DELETE FROM images WHERE id = %s;", (img_id,))
                            
                            if fixed < 10:
                                print(f"  🗑️ Deleted duplicate: {image_id}")
                                print(f"     (keeping: {new_image_id})")
                            
                            fixed += 1
                        else:
                            # No underscored version - update this entry
                            cur.execute("""
                                UPDATE images 
                                SET image_id = %s,
                                    thumbnail_path = %s,
                                    highres_path = %s
                                WHERE id = %s;
                            """, (new_image_id, new_thumb, new_highres, img_id))
                            
                            if fixed < 10:
                                print(f"  ✓ Updated: {image_id}")
                                print(f"    → {new_image_id}")
                            
                            fixed += 1
                
                fixed += 1
                
                if fixed <= 10:
                    print(f"  ✓ Fixed: {image_id}")
                    print(f"    → {new_image_id}")
                elif fixed == 11:
                    print(f"  ... fixing {len(images_with_spaces) - 10} more ...")
                
            except Exception as e:
                print(f"  ✗ Error: {image_id}: {e}")
                errors += 1
        
        conn.close()
        
        print()
        print("=" * 70)
        print("✓ Fix Complete!")
        print("=" * 70)
        print(f"Fixed: {fixed}")
        print(f"Skipped: {skipped} (underscored file doesn't exist)")
        print(f"Errors: {errors}")
        print()
        
        return True
        
    except Exception as e:
        print(f"Database error: {e}")
        return False

if __name__ == '__main__':
    import sys
    
    print()
    print("This script will:")
    print("  1. Find all database entries with spaces in paths")
    print("  2. Update them to use underscored versions")
    print("  3. Only if the underscored file actually exists")
    print()
    
    if not fix_spaced_filenames():
        sys.exit(1)
    
    print("Database updated! Reload website to see all images.")
