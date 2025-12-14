#!/usr/bin/env python3
"""
Cleanup script for hash character (#) to 'n' migration.
This script:
1. Updates database paths from #1 to n1 format
2. Optionally removes old directories with # characters
"""

import os
import sys
import psycopg2
from pathlib import Path

# Database configuration
DB_CONFIG = {
    'database': 'imagearchive',
    'user': 'postgres',
    'password': 'xxxxx',
    'host': '172.16.8.26',
    'port': '5432'
}

# Target library path
TARGET_LIBRARY = "/opt/media"

def update_database_paths():
    """Update all database paths to replace #1, #2, etc. with n1, n2, etc."""
    
    print("=" * 70)
    print("Hash Character Migration - Database Update")
    print("=" * 70)
    print()
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        # First, get all images to update
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, image_id, thumbnail_path, highres_path 
                FROM images 
                WHERE image_id LIKE '%#%' 
                   OR thumbnail_path LIKE '%#%' 
                   OR highres_path LIKE '%#%';
            """)
            images_to_update = cur.fetchall()
        
        if not images_to_update:
            print("✓ No images with # characters found in database")
            print("  Database is already clean!")
            conn.close()
            return True
        
        print(f"Found {len(images_to_update)} images with # characters")
        print()
        
        updated = 0
        errors = 0
        
        # Process each image in its own transaction
        for img_id, image_id, thumbnail_path, highres_path in images_to_update:
            try:
                with conn:  # Separate transaction for each image
                    with conn.cursor() as cur:
                        # Replace # with n in all paths
                        new_image_id = image_id.replace('#', 'n')
                        new_thumbnail = thumbnail_path.replace('#', 'n') if thumbnail_path else None
                        new_highres = highres_path.replace('#', 'n') if highres_path else None
                        
                        # Check if the 'n' version already exists
                        cur.execute("SELECT id FROM images WHERE image_id = %s;", (new_image_id,))
                        duplicate = cur.fetchone()
                        
                        if duplicate:
                            # The 'n' version already exists - delete the old '#' entry
                            cur.execute("DELETE FROM images WHERE id = %s;", (img_id,))
                            updated += 1
                            
                            if updated <= 10:
                                print(f"  🗑️  Deleted duplicate: {image_id}")
                                print(f"     (keeping: {new_image_id})")
                            elif updated == 11:
                                print(f"  ... deleting {len(images_to_update) - 10} more duplicates ...")
                        else:
                            # The 'n' version doesn't exist yet - update this entry
                            cur.execute("""
                                UPDATE images 
                                SET image_id = %s,
                                    thumbnail_path = %s,
                                    highres_path = %s
                                WHERE id = %s;
                            """, (new_image_id, new_thumbnail, new_highres, img_id))
                            
                            updated += 1
                            
                            if updated <= 10:
                                print(f"  ✓ Updated: {image_id}")
                                print(f"    → {new_image_id}")
                
            except Exception as e:
                print(f"  ✗ Error processing {image_id}: {e}")
                errors += 1
                # Continue with next image
        
        conn.close()
        
        print()
        print("=" * 70)
        print(f"✓ Database Update Complete!")
        print("=" * 70)
        print(f"Updated: {updated}")
        print(f"Errors: {errors}")
        print()
        
        return True
        
    except Exception as e:
        print(f"Database error: {e}")
        return False

def find_old_directories():
    """Find directories with # characters that should be removed."""
    
    print()
    print("=" * 70)
    print("Finding Old Directories with # Characters")
    print("=" * 70)
    print()
    
    old_dirs = []
    
    for film_type in ['rollfilm', 'sheetfilm']:
        film_dir = os.path.join(TARGET_LIBRARY, film_type)
        if not os.path.isdir(film_dir):
            continue
        
        for entry in os.scandir(film_dir):
            if entry.is_dir() and '#' in entry.name:
                # Check if corresponding 'n' version exists
                new_name = entry.name.replace('#', 'n')
                new_path = os.path.join(film_dir, new_name)
                
                # Add to removal list (will remove even if new version doesn't exist,
                # since these are generated files, not originals)
                old_dirs.append({
                    'old': entry.path,
                    'new': new_path if os.path.exists(new_path) else None,
                    'name': entry.name,
                    'new_name': new_name
                })
    
    if not old_dirs:
        print("✓ No old directories with # characters found")
        print("  Filesystem is already clean!")
        return []
    
    print(f"Found {len(old_dirs)} old directories:\n")
    
    for i, dir_info in enumerate(old_dirs, 1):
        print(f"{i}. {dir_info['name']}")
        if dir_info['new']:
            print(f"   ✓ New version exists: {dir_info['new_name']}")
        else:
            print(f"   ⚠ New version NOT found (will still delete - these are generated files)")
    
    return old_dirs

def remove_old_directories(old_dirs):
    """Remove old directories after confirmation."""
    
    if not old_dirs:
        return
    
    print()
    print("=" * 70)
    print("Remove Old Directories")
    print("=" * 70)
    print()
    print("⚠️  WARNING: This will DELETE the old directories with # characters")
    print("   The new versions (with 'n') will be kept.")
    print()
    
    response = input(f"Delete {len(old_dirs)} old directories? [yes/NO]: ").strip().lower()
    
    if response != 'yes':
        print("Cancelled. Old directories kept.")
        return
    
    print()
    removed = 0
    errors = 0
    
    for dir_info in old_dirs:
        try:
            import shutil
            shutil.rmtree(dir_info['old'])
            print(f"  ✓ Removed: {dir_info['name']}")
            removed += 1
        except Exception as e:
            print(f"  ✗ Error removing {dir_info['name']}: {e}")
            errors += 1
    
    print()
    print("=" * 70)
    print(f"✓ Cleanup Complete!")
    print("=" * 70)
    print(f"Removed: {removed}")
    print(f"Errors: {errors}")
    print()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Cleanup hash character migration')
    parser.add_argument('--auto-remove', action='store_true',
                        help='Automatically remove old directories without confirmation')
    
    args = parser.parse_args()
    
    print()
    print("This script will:")
    print("  1. Update database to replace # with n in all paths")
    print("  2. Find old directories with # characters")
    print("  3. Optionally remove old directories")
    print()
    
    # Step 1: Update database
    if not update_database_paths():
        print("Database update failed!")
        sys.exit(1)
    
    # Step 2: Find old directories
    old_dirs = find_old_directories()
    
    # Step 3: Remove old directories
    if old_dirs:
        if args.auto_remove:
            print("\n--auto-remove flag set, removing directories...")
            import shutil
            for dir_info in old_dirs:
                try:
                    shutil.rmtree(dir_info['old'])
                    print(f"  ✓ Removed: {dir_info['name']}")
                except Exception as e:
                    print(f"  ✗ Error: {e}")
        else:
            remove_old_directories(old_dirs)
    
    print()
    print("Migration complete! Your archive is now clean.")
    print()
    print("Next steps:")
    print("  1. Restart API server if running")
    print("  2. Reload website (Ctrl+Shift+R)")
    print("  3. Images should now load correctly")

if __name__ == '__main__':
    main()
