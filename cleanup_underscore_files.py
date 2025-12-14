#!/usr/bin/env python3
"""
Cleanup script to remove ._ files from database.
These are macOS resource fork files that shouldn't have been imported.
"""

import psycopg2

# Database configuration
DB_CONFIG = {
    'database': 'imagearchive',
    'user': 'postgres',
    'password': 'xxxxx',
    'host': '172.16.8.26',
    'port': '5432'
}

def cleanup_underscore_files():
    """Remove all images with ._ in their paths from database."""
    
    print("=" * 70)
    print("Cleanup ._ Files from Database")
    print("=" * 70)
    print()
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        # First, find all images with ._ pattern
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, image_id 
                FROM images 
                WHERE image_id LIKE '%/._/%' 
                   OR filename_base LIKE '._%'
                   OR image_id LIKE '%/._%';
            """)
            images_to_delete = cur.fetchall()
        
        if not images_to_delete:
            print("✓ No ._ files found in database")
            print("  Database is clean!")
            conn.close()
            return True
        
        print(f"Found {len(images_to_delete)} images with ._ pattern:\n")
        
        # Show first 10
        for i, (img_id, image_id) in enumerate(images_to_delete[:10], 1):
            print(f"  {i}. {image_id}")
        
        if len(images_to_delete) > 10:
            print(f"  ... and {len(images_to_delete) - 10} more")
        
        print()
        response = input(f"Delete {len(images_to_delete)} entries from database? [yes/NO]: ").strip().lower()
        
        if response != 'yes':
            print("Cancelled.")
            conn.close()
            return False
        
        print()
        print("Deleting entries...")
        
        deleted = 0
        errors = 0
        
        # Delete each in its own transaction
        for img_id, image_id in images_to_delete:
            try:
                with conn:
                    with conn.cursor() as cur:
                        # Delete from image_tags first (foreign key)
                        cur.execute("DELETE FROM image_tags WHERE image_id = %s;", (img_id,))
                        
                        # Delete from images
                        cur.execute("DELETE FROM images WHERE id = %s;", (img_id,))
                        
                        deleted += 1
                        
                        if deleted <= 10:
                            print(f"  ✓ Deleted: {image_id}")
                        elif deleted == 11:
                            print(f"  ... deleting {len(images_to_delete) - 10} more ...")
                
            except Exception as e:
                print(f"  ✗ Error deleting {image_id}: {e}")
                errors += 1
        
        conn.close()
        
        print()
        print("=" * 70)
        print("✓ Cleanup Complete!")
        print("=" * 70)
        print(f"Deleted: {deleted}")
        print(f"Errors: {errors}")
        print()
        
        if deleted > 0:
            print("Database cleaned successfully!")
            print()
            print("Next steps:")
            print("  1. Reload website (Ctrl+Shift+R)")
            print("  2. ._ files will no longer appear in gallery")
        
        return True
        
    except Exception as e:
        print(f"Database error: {e}")
        return False

if __name__ == '__main__':
    import sys
    
    print()
    print("This script will remove all database entries for ._ files")
    print("(macOS resource fork files that shouldn't be in the archive)")
    print()
    
    if not cleanup_underscore_files():
        sys.exit(1)
