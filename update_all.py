#!/usr/bin/env python3
"""
Unified ImageArchive Update Script
Combines: process images → scan library → update database
All in one efficient Python script!
"""

import os
import sys
import json
import subprocess
import hashlib
import time
from pathlib import Path
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
from PIL.TiffImagePlugin import IFDRational
from fractions import Fraction
import psycopg2

# ============================================================================
# CONFIGURATION
# ============================================================================

# Source directories (with symlinks to batches)
SOURCE_ROLLFILM = "/mnt/omv/Photo/Collected/Rollfilm"
SOURCE_SHEETFILM = "/mnt/omv/Photo/Collected/Sheetfilm"

# Target library (where scaled images are stored)
TARGET_LIBRARY = "/mnt/omv/Photo/Picture_library"

# Path translation for database storage
# Scanner sees this path:    /mnt/omv/Photo/Picture_library
# Database should store:     /opt/media
PATH_SCANNER = "/mnt/omv/Photo/Picture_library"
PATH_DATABASE = "/opt/media"

# Image sizes
SIZE_SMALL = "600x600>"
SIZE_LARGE = "2560x2560>"

# Database configuration
DB_CONFIG = {
    'database': 'imagearchive',
    'user': 'postgres',
    'password': 'xxxxx',
    'host': '172.16.8.26',
    'port': '5432'
}

# Index file for tracking processed images
INDEX_FILE = f"{TARGET_LIBRARY}/.processing_index"

# Detect available tools
USE_EXIFTOOL = subprocess.run(['which', 'exiftool'], capture_output=True).returncode == 0

# Detect ImageMagick command (v7 uses 'magick', v6 uses 'convert')
if subprocess.run(['which', 'magick'], capture_output=True).returncode == 0:
    IMAGEMAGICK_CMD = 'magick'
elif subprocess.run(['which', 'convert'], capture_output=True).returncode == 0:
    IMAGEMAGICK_CMD = 'convert'
else:
    print("ERROR: ImageMagick not found. Please install ImageMagick.")
    sys.exit(1)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def sanitize_filename(text):
    """Sanitize filename for URL-safe and filesystem-safe names."""
    # Replace spaces with underscores
    text = text.replace(' ', '_')
    # Replace # with n (hash symbols can cause issues in URLs and shells)
    text = text.replace('#', 'n')
    return text

def translate_path_for_db(scanner_path):
    """Translate scanner path to database path."""
    if scanner_path.startswith(PATH_SCANNER):
        return scanner_path.replace(PATH_SCANNER, PATH_DATABASE, 1)
    return scanner_path

def get_file_signature(filepath):
    """Get file signature (mtime:size) for change detection."""
    try:
        stat = os.stat(filepath)
        return f"{int(stat.st_mtime)}:{stat.st_size}"
    except:
        return "0:0"

def load_index():
    """Load processing index."""
    index = {}
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, 'r') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) == 3:
                    key = f"{parts[0]}|{parts[1]}"
                    index[key] = parts[2]
    return index

def save_index_entry(index, source, target, signature):
    """Save entry to index."""
    key = f"{source}|{target}"
    index[key] = signature

def write_index(index):
    """Write index to file."""
    with open(INDEX_FILE, 'w') as f:
        for key, sig in index.items():
            f.write(f"{key}|{sig}\n")

def needs_update(source_file, target_file, index):
    """Check if file needs processing."""
    if not os.path.exists(target_file):
        return True
    
    # Check index
    key = f"{source_file}|{target_file}"
    source_sig = get_file_signature(source_file)
    
    if key in index and index[key] == source_sig:
        return False  # Up to date
    
    # Check modification time
    if os.path.getmtime(source_file) > os.path.getmtime(target_file):
        return True
    
    return False

def process_image(source_path, output_path, size):
    """Process image with EXIF preservation."""
    try:
        temp_file = f"{output_path}.tmp.jpg"
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        if USE_EXIFTOOL:
            # Method 1: Resize with ImageMagick, then copy EXIF with exiftool
            if IMAGEMAGICK_CMD == 'magick':
                cmd = [
                    'magick', f'{source_path}[0]',
                    '-quiet', '-auto-orient',
                    '-resize', size,
                    '-quality', '85',
                    temp_file
                ]
            else:
                # ImageMagick v6 (convert command)
                cmd = [
                    'convert', f'{source_path}[0]',
                    '-auto-orient',
                    '-resize', size,
                    '-quality', '85',
                    temp_file
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0 and result.stderr:
                # Filter out harmless TIFF warnings
                errors = [line for line in result.stderr.split('\n') 
                         if line and 'Wrong data type' not in line and 'tag ignored' not in line]
                if errors:
                    print(f"      ImageMagick warnings: {errors[0]}")
            
            if not os.path.exists(temp_file):
                print(f"      ERROR: Failed to resize image")
                return False
            
            # Copy EXIF with exiftool
            subprocess.run([
                'exiftool', '-TagsFromFile', source_path,
                '-all:all', '-overwrite_original', temp_file
            ], capture_output=True)
            
            os.rename(temp_file, output_path)
        else:
            # Method 2: ImageMagick only (preserves most EXIF)
            if IMAGEMAGICK_CMD == 'magick':
                cmd = [
                    'magick', f'{source_path}[0]',
                    '-quiet', '-auto-orient',
                    '-resize', size,
                    '-quality', '85',
                    output_path
                ]
            else:
                # ImageMagick v6
                cmd = [
                    'convert', f'{source_path}[0]',
                    '-auto-orient',
                    '-resize', size,
                    '-quality', '85',
                    output_path
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if not os.path.exists(output_path):
                if result.stderr:
                    print(f"      ERROR: {result.stderr.split(chr(10))[0]}")
                return False
        
        # Clean up temp files
        parent_dir = Path(os.path.dirname(output_path))
        for f in parent_dir.glob(f"{os.path.basename(output_path)}.tmp*.jpg"):
            f.unlink()
        
        return True
    except Exception as e:
        print(f"      ERROR: {e}")
        return False

# ============================================================================
# EXIF EXTRACTION
# ============================================================================

def convert_to_serializable(obj):
    """Convert EXIF values to JSON-serializable types."""
    if isinstance(obj, IFDRational):
        return float(obj)
    elif isinstance(obj, bytes):
        try:
            # Decode and remove null bytes that PostgreSQL can't handle
            decoded = obj.decode('utf-8', errors='ignore')
            return decoded.replace('\x00', '').replace('\u0000', '')
        except:
            return str(obj).replace('\x00', '').replace('\u0000', '')
    elif isinstance(obj, str):
        # Remove null bytes from strings
        return obj.replace('\x00', '').replace('\u0000', '')
    elif isinstance(obj, (list, tuple)):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    else:
        return obj

def format_focal_length(focal_length):
    """Format focal length nicely."""
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
    """Format aperture nicely."""
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
    """Format shutter speed nicely."""
    if not exposure_time:
        return ''
    try:
        if isinstance(exposure_time, (IFDRational, Fraction)):
            exposure_time = float(exposure_time)
        if isinstance(exposure_time, (int, float)):
            if exposure_time < 1:
                return f"1/{int(1/exposure_time)}"
            else:
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
        
        # Convert EXIF tags to readable names
        exif = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            exif[tag] = convert_to_serializable(value)
        
        # Extract commonly needed fields
        result = {
            'camera_make': str(exif.get('Make', '')).strip() if exif.get('Make') else '',
            'camera_model': str(exif.get('Model', '')).strip() if exif.get('Model') else '',
            'lens_model': str(exif.get('LensModel', '')).strip() if exif.get('LensModel') else '',
            'focal_length': format_focal_length(exif.get('FocalLength')),
            'aperture': format_aperture(exif.get('FNumber')),
            'shutter_speed': format_shutter_speed(exif.get('ExposureTime')),
            'iso': str(exif.get('ISOSpeedRatings', '')) if exif.get('ISOSpeedRatings') else '',
            'date_taken': None,
            'exif_data': exif
        }
        
        # Parse date taken
        date_str = exif.get('DateTimeOriginal') or exif.get('DateTime')
        if date_str:
            try:
                result['date_taken'] = datetime.strptime(str(date_str), '%Y:%m:%d %H:%M:%S').isoformat()
            except:
                pass
        
        return result
    except:
        return None

def parse_path(full_path, base_dir):
    """Parse image path to extract metadata."""
    relative_path = os.path.relpath(full_path, base_dir)
    parts = relative_path.split(os.sep)
    
    if len(parts) < 4:
        return None, None
    
    film_type = parts[0]  # rollfilm or sheetfilm
    batch_info = parts[1]
    filename_base = parts[2]
    resolution = parts[3]
    
    # Extract film stock from batch_info
    film_stock = batch_info.split('_med_')[-1] if '_med_' in batch_info else 'Unknown'
    
    # Construct image_id
    image_id = f"{film_type}/{batch_info}/{filename_base}"
    
    return image_id, {
        'film_type': film_type,
        'batch_info': batch_info,
        'filename_base': filename_base,
        'film_stock': film_stock,
        'resolution': resolution
    }

# ============================================================================
# MAIN PROCESSING
# ============================================================================

def get_marked_images():
    """Get list of images marked for reload from database."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT image_id, thumbnail_path, highres_path 
                FROM images 
                WHERE needs_reload = TRUE;
            """)
            marked = cur.fetchall()
        conn.close()
        return marked
    except Exception as e:
        print(f"Error fetching marked images: {e}")
        return []

def clear_reload_flags(image_ids):
    """Clear reload flags after processing."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn:
            with conn.cursor() as cur:
                for image_id in image_ids:
                    cur.execute("UPDATE images SET needs_reload = FALSE WHERE image_id = %s;", (image_id,))
        conn.close()
        print(f"[RELOAD] Cleared reload flags for {len(image_ids)} images")
    except Exception as e:
        print(f"Error clearing reload flags: {e}")

def process_all(reload_marked_only=False):
    """Main function that does everything."""
    
    print("=" * 70)
    print("ImageArchive Unified Update Script")
    print("=" * 70)
    print()
    
    # Check if we're only reloading marked images
    if reload_marked_only:
        print("MODE: Reload marked images only")
        print()
        marked_images = get_marked_images()
        
        if not marked_images:
            print("✓ No images marked for reload")
            return True
        
        print(f"Found {len(marked_images)} images marked for reload:\n")
        for i, (image_id, thumb, highres) in enumerate(marked_images[:10], 1):
            print(f"  {i}. {image_id}")
        if len(marked_images) > 10:
            print(f"  ... and {len(marked_images) - 10} more")
        print()
    
    # Load index
    print("[1/4] Loading processing index...")
    index = load_index()
    print(f"      Found {len(index)} tracked files")
    
    # Statistics
    stats = {
        'processed': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0
    }
    
    images_data = {}
    
    # ========================================================================
    # STEP 1: Process source images (bash script equivalent)
    # ========================================================================
    print()
    print("[2/4] Processing source images...")
    print("-" * 70)
    
    for film_type, source_dir in [('rollfilm', SOURCE_ROLLFILM), ('sheetfilm', SOURCE_SHEETFILM)]:
        print(f"\n📁 Processing {film_type}...")
        
        if not os.path.isdir(source_dir):
            print(f"   ⚠ Source directory not found: {source_dir}")
            continue
        
        # Find all symlinks (batch directories)
        for entry in os.scandir(source_dir):
            if not entry.is_symlink() or entry.name.startswith('.'):
                continue
            
            try:
                source_batch_dir = os.path.realpath(entry.path)
                source_batch_name = entry.name
                target_batch_name = sanitize_filename(source_batch_name)
                target_batch_dir = os.path.join(TARGET_LIBRARY, film_type, target_batch_name)
                
                os.makedirs(target_batch_dir, exist_ok=True)
                
                print(f"\n   📂 {source_batch_name}")
                if source_batch_name != target_batch_name:
                    print(f"      → {target_batch_name}")
                
                batch_stats = {'new': 0, 'updated': 0, 'skipped': 0}
                
                # Find all images - search current dir and one level deeper
                batch_files = {}
                
                def scan_for_images(scan_dir, depth=0):
                    """Scan directory for image files (up to 1 level deep)."""
                    if depth > 1:
                        return
                    
                    for item in os.scandir(scan_dir):
                        if item.is_file():
                            filename = item.name
                            
                            # Skip hidden/temp/part files
                            if (filename.startswith('._') or 
                                filename.startswith('.') or 
                                filename.startswith('part_')):
                                continue
                            
                            ext = filename.lower()
                            if not (ext.endswith('.jpg') or ext.endswith('.jpeg') or 
                                    ext.endswith('.tif') or ext.endswith('.tiff')):
                                continue
                            
                            basename = os.path.splitext(filename)[0]
                            
                            # Group files by basename (prefer .jpg over .tif)
                            if basename not in batch_files:
                                batch_files[basename] = item
                            else:
                                # Prefer JPEG over TIFF
                                existing_ext = os.path.splitext(batch_files[basename].name)[1].lower()
                                current_ext = os.path.splitext(filename)[1].lower()
                                if current_ext in ['.jpg', '.jpeg'] and existing_ext in ['.tif', '.tiff']:
                                    batch_files[basename] = item
                        elif item.is_dir() and not item.name.startswith('.') and depth < 1:
                            # Recurse one level deeper (max depth = 1)
                            scan_for_images(item.path, depth + 1)
                
                # Scan source batch directory and one level deeper
                scan_for_images(source_batch_dir, depth=0)
                
                # Process deduplicated files
                for basename, image_file in batch_files.items():
                    filename = image_file.name
                    basename_clean = sanitize_filename(basename)
                    
                    # Create output structure
                    image_dir = os.path.join(target_batch_dir, basename_clean)
                    os.makedirs(os.path.join(image_dir, '600'), exist_ok=True)
                    os.makedirs(os.path.join(image_dir, '2560'), exist_ok=True)
                    
                    small_output = os.path.join(image_dir, '600', f'{basename_clean}.jpg')
                    large_output = os.path.join(image_dir, '2560', f'{basename_clean}.jpg')
                    
                    # Check if update needed
                    small_needs = needs_update(image_file.path, small_output, index)
                    large_needs = needs_update(image_file.path, large_output, index)
                    
                    if not small_needs and not large_needs:
                        batch_stats['skipped'] += 1
                        continue
                    
                    is_update = os.path.exists(small_output) and os.path.exists(large_output)
                    
                    if is_update:
                        print(f"      ↻ {filename}")
                        batch_stats['updated'] += 1
                    else:
                        print(f"      ✓ {filename}")
                        batch_stats['new'] += 1
                    
                    # Try processing, with fallback to JPEG if TIFF fails
                    current_source = image_file.path
                    
                    # Process 600px
                    if small_needs:
                        success = process_image(current_source, small_output, SIZE_SMALL)
                        
                        # If TIFF failed, try JPEG version if it exists
                        if not success and current_source.lower().endswith(('.tif', '.tiff')):
                            jpg_version = os.path.splitext(current_source)[0] + '.jpg'
                            if os.path.exists(jpg_version):
                                print(f"      → Fallback to JPEG version")
                                success = process_image(jpg_version, small_output, SIZE_SMALL)
                                if success:
                                    current_source = jpg_version
                        
                        if success:
                            save_index_entry(index, current_source, small_output, 
                                           get_file_signature(current_source))
                        else:
                            stats['errors'] += 1
                    
                    # Process 2560px
                    if large_needs:
                        success = process_image(current_source, large_output, SIZE_LARGE)
                        
                        # If TIFF failed, try JPEG version if it exists
                        if not success and current_source.lower().endswith(('.tif', '.tiff')):
                            jpg_version = os.path.splitext(current_source)[0] + '.jpg'
                            if os.path.exists(jpg_version):
                                print(f"      → Fallback to JPEG version")
                                success = process_image(jpg_version, large_output, SIZE_LARGE)
                                if success:
                                    current_source = jpg_version
                        
                        if success:
                            save_index_entry(index, current_source, large_output,
                                           get_file_signature(current_source))
                        else:
                            stats['errors'] += 1
                    
                    # Store for scanning phase
                    image_id = f"{film_type}/{target_batch_name}/{basename_clean}"
                    if image_id not in images_data:
                        images_data[image_id] = {
                            'image_id': image_id,
                            'film_type': film_type,
                            'batch_info': target_batch_name,
                            'filename_base': basename_clean,
                            'film_stock': target_batch_name.split('_med_')[-1] if '_med_' in target_batch_name else 'Unknown',
                            'thumbnail_path': None,
                            'highres_path': None,
                            'description': ''
                        }
                    
                    images_data[image_id]['thumbnail_path'] = small_output
                    images_data[image_id]['highres_path'] = large_output
                
                if batch_stats['new'] or batch_stats['updated']:
                    print(f"      Summary: {batch_stats['new']} new, {batch_stats['updated']} updated, {batch_stats['skipped']} skipped")
                
                stats['processed'] += batch_stats['new']
                stats['updated'] += batch_stats['updated']
                stats['skipped'] += batch_stats['skipped']
                
            except Exception as e:
                print(f"   ✗ Error processing batch {entry.name}: {e}")
                stats['errors'] += 1
    
    # Save index
    write_index(index)
    
    print()
    print("-" * 70)
    print(f"Image processing complete: {stats['processed']} new, {stats['updated']} updated, {stats['skipped']} skipped")
    
    # ========================================================================
    # STEP 2: Scan library and extract EXIF (library_scanner.py equivalent)
    # ========================================================================
    print()
    print("[3/4] Scanning library and extracting EXIF...")
    print("-" * 70)
    
    # Also scan existing files in target library
    for film_type in ['rollfilm', 'sheetfilm']:
        film_dir = os.path.join(TARGET_LIBRARY, film_type)
        if not os.path.isdir(film_dir):
            continue
        
        for batch_dir in os.scandir(film_dir):
            if not batch_dir.is_dir() or batch_dir.name.startswith('.'):
                continue
            
            for image_dir in os.scandir(batch_dir.path):
                if not image_dir.is_dir():
                    continue
                
                image_id = f"{film_type}/{batch_dir.name}/{image_dir.name}"
                
                # Find 600 and 2560 versions
                small_path = os.path.join(image_dir.path, '600', f'{image_dir.name}.jpg')
                large_path = os.path.join(image_dir.path, '2560', f'{image_dir.name}.jpg')
                
                if os.path.exists(small_path) and os.path.exists(large_path):
                    if image_id not in images_data:
                        images_data[image_id] = {
                            'image_id': image_id,
                            'film_type': film_type,
                            'batch_info': batch_dir.name,
                            'filename_base': image_dir.name,
                            'film_stock': batch_dir.name.split('_med_')[-1] if '_med_' in batch_dir.name else 'Unknown',
                            'thumbnail_path': small_path,
                            'highres_path': large_path,
                            'description': ''
                        }
                    else:
                        images_data[image_id]['thumbnail_path'] = small_path
                        images_data[image_id]['highres_path'] = large_path
    
    # Extract EXIF from high-res images
    exif_count = 0
    for image_id, data in images_data.items():
        if data.get('highres_path'):
            exif = extract_exif(data['highres_path'])
            if exif:
                data.update({
                    'camera_make': str(exif.get('camera_make', '')),
                    'camera_model': str(exif.get('camera_model', '')),
                    'lens_model': str(exif.get('lens_model', '')),
                    'focal_length': str(exif.get('focal_length', '')),
                    'aperture': str(exif.get('aperture', '')),
                    'shutter_speed': str(exif.get('shutter_speed', '')),
                    'iso': str(exif.get('iso', '')),
                    'date_taken': exif.get('date_taken', ''),
                    'exif_data': exif.get('exif_data', {})
                })
                exif_count += 1
    
    image_list = list(images_data.values())
    print(f"Found {len(image_list)} complete image pairs")
    print(f"Extracted EXIF from {exif_count} images")
    
    # Save to JSON
    json_file = '../image_data.json'
    with open(json_file, 'w') as f:
        json.dump(image_list, f, indent=4, default=str)
    print(f"Saved to {json_file}")
    
    # ========================================================================
    # STEP 3: Update database (update_database.py equivalent)
    # ========================================================================
    print()
    print("[4/4] Updating database...")
    print("-" * 70)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False  # Use transactions, but commit per image
        
        db_stats = {'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
        
        for image in image_list:
            try:
                with conn:  # Each image in its own transaction
                    with conn.cursor() as cur:
                        image_id = image['image_id']
                        
                        # Translate paths from scanner to database paths
                        thumbnail_db = translate_path_for_db(image['thumbnail_path'])
                        highres_db = translate_path_for_db(image['highres_path'])
                        
                        # Check if exists
                        cur.execute("SELECT id FROM images WHERE image_id = %s;", (image_id,))
                        existing = cur.fetchone()
                        
                        if existing:
                            # Update EXIF data
                            update_sql = """
                                UPDATE images 
                                SET camera_make = %s, camera_model = %s, lens_model = %s,
                                    focal_length = %s, aperture = %s, shutter_speed = %s,
                                    iso = %s, date_taken = %s, exif_data = %s::jsonb,
                                    thumbnail_path = %s, highres_path = %s
                                WHERE image_id = %s;
                            """
                            # Prepare EXIF JSON - remove null bytes that PostgreSQL can't handle
                            if image.get('exif_data'):
                                exif_json = json.dumps(image.get('exif_data', {}))
                                exif_json = exif_json.replace('\\u0000', '').replace('\x00', '')
                            else:
                                exif_json = None
                            
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
                                thumbnail_db,
                                highres_db,
                                image_id
                            ))
                            db_stats['updated'] += 1
                        else:
                            # Insert new image
                            insert_sql = """
                                INSERT INTO images 
                                (image_id, film_type, batch_info, filename_base, film_stock,
                                 thumbnail_path, highres_path, description,
                                 camera_make, camera_model, lens_model, focal_length,
                                 aperture, shutter_speed, iso, date_taken, exif_data)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb);
                            """
                            # Prepare EXIF JSON - remove null bytes that PostgreSQL can't handle
                            if image.get('exif_data'):
                                exif_json = json.dumps(image.get('exif_data', {}))
                                exif_json = exif_json.replace('\\u0000', '').replace('\x00', '')
                            else:
                                exif_json = None
                            
                            cur.execute(insert_sql, (
                                image_id,
                                image['film_type'],
                                image['batch_info'],
                                image['filename_base'],
                                image['film_stock'],
                                thumbnail_db,
                                highres_db,
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
                            db_stats['inserted'] += 1
                        
                        # Transaction auto-commits when exiting 'with conn:' block
                            
            except Exception as e:
                # Transaction will rollback automatically
                print(f"   ✗ Error: {image.get('image_id', 'unknown')}: {e}")
                db_stats['errors'] += 1
                # Continue with next image
        
        conn.close()
        
        print(f"Database updated: {db_stats['inserted']} new, {db_stats['updated']} updated")
        
        # Verify
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM images;")
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM images WHERE camera_model IS NOT NULL AND camera_model != '';")
            with_exif = cur.fetchone()[0]
        conn.close()
        
        print(f"Total images in database: {total}")
        print(f"Images with EXIF data: {with_exif}")
        
    except Exception as e:
        print(f"Database error: {e}")
        return False
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print()
    print("=" * 70)
    print("✓ Update Complete!")
    print("=" * 70)
    print(f"Images processed:  {stats['processed']}")
    print(f"Images updated:    {stats['updated']}")
    print(f"Images skipped:    {stats['skipped']}")
    print(f"Errors:            {stats['errors']}")
    print()
    print("Database is up to date with latest images and EXIF data!")
    print()
    
    return True

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Unified ImageArchive update script')
    parser.add_argument('--skip-processing', action='store_true',
                        help='Skip image processing, only scan and update database')
    parser.add_argument('--reload-marked', action='store_true',
                        help='Only reload images marked with needs_reload flag')
    
    args = parser.parse_args()
    
    start_time = time.time()
    
    if not process_all(reload_marked_only=args.reload_marked):
        sys.exit(1)
    
    elapsed = time.time() - start_time
    print(f"Total time: {elapsed:.1f}s")
