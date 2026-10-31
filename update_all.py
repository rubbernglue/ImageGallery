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
import shutil
import tempfile
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

# Cache of pixel fingerprints (used to recognise renamed images)
FINGERPRINT_CACHE_FILE = f"{TARGET_LIBRARY}/.fingerprint_cache"

# Safety limit: --prune refuses to delete more than this fraction of the library in one run
PRUNE_MAX_FRACTION = 0.10

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

def needs_update(source_file, target_file, index, force=False):
    """Check if file needs processing."""
    if force or not os.path.exists(target_file):
        return True

    key = f"{source_file}|{target_file}"
    if key in index:
        # Any change in mtime or size means the source was edited. Don't also require a newer
        # mtime: some EXIF tools (e.g. exiftool -P) keep the original modification time.
        return index[key] != get_file_signature(source_file)

    # Not tracked yet (e.g. index file lost): fall back to comparing modification times
    return os.path.getmtime(source_file) > os.path.getmtime(target_file)

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
                    '-limit', 'memory', '2GiB',
                    '-limit', 'map', '4GiB',
                    '-quiet', '-auto-orient',
                    '-resize', size,
                    '-quality', '85',
                    temp_file
                ]
            else:
                # ImageMagick v6 (convert command)
                cmd = [
                    'convert', f'{source_path}[0]',
                    '-limit', 'memory', '2GiB',
                    '-limit', 'map', '4GiB',
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
                    '-limit', 'memory', '2GiB',
                    '-limit', 'map', '4GiB',
                    '-quiet', '-auto-orient',
                    '-resize', size,
                    '-quality', '85',
                    output_path
                ]
            else:
                # ImageMagick v6
                cmd = [
                    'convert', f'{source_path}[0]',
                    '-limit', 'memory', '2GiB',
                    '-limit', 'map', '4GiB',
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
# CONTENT FINGERPRINTS (rename detection)
# ============================================================================

def compute_content_hash(image_path):
    """SHA-256 of the decoded pixels (plus size) of an image.

    EXIF and the file name are not part of the hash, so it stays the same when a
    file is renamed or only its metadata is edited.
    """
    try:
        with Image.open(image_path) as img:
            rgb = img.convert('RGB')
            digest = hashlib.sha256()
            digest.update(f"{rgb.width}x{rgb.height}".encode())
            digest.update(rgb.tobytes())
            return digest.hexdigest()
    except Exception as e:
        print(f"      ⚠ Could not fingerprint {image_path}: {e}")
        return None

def load_fingerprint_cache():
    """Load cached fingerprints: path -> (signature, hash)."""
    cache = {}
    if os.path.exists(FINGERPRINT_CACHE_FILE):
        with open(FINGERPRINT_CACHE_FILE, 'r') as f:
            for line in f:
                parts = line.rstrip('\n').rsplit('|', 2)
                if len(parts) == 3:
                    cache[parts[0]] = (parts[1], parts[2])
    return cache

def write_fingerprint_cache(cache):
    """Write the fingerprint cache, dropping entries for files that no longer exist."""
    with open(FINGERPRINT_CACHE_FILE, 'w') as f:
        for path, (signature, content_hash) in cache.items():
            if os.path.exists(path):
                f.write(f"{path}|{signature}|{content_hash}\n")

def get_content_hash(image_path, cache):
    """Fingerprint of an image, reusing the cache while the file is unchanged."""
    if not image_path or not os.path.exists(image_path):
        return None
    signature = get_file_signature(image_path)
    cached = cache.get(image_path)
    if cached and cached[0] == signature:
        return cached[1]
    content_hash = compute_content_hash(image_path)
    if content_hash:
        cache[image_path] = (signature, content_hash)
    return content_hash

# ============================================================================
# SOURCE AND LIBRARY SCANNING
# ============================================================================

def find_batch_images(batch_dir):
    """Find image files in a batch directory and one level of subdirectories.

    Returns basename -> DirEntry, preferring JPEG over TIFF when both exist.
    """
    batch_files = {}

    def scan(scan_dir, depth):
        for item in os.scandir(scan_dir):
            if item.is_file():
                filename = item.name
                # Skip hidden/temp/part files
                if filename.startswith('.') or filename.startswith('part_'):
                    continue
                ext = os.path.splitext(filename)[1].lower()
                if ext not in ('.jpg', '.jpeg', '.tif', '.tiff'):
                    continue
                basename = os.path.splitext(filename)[0]
                if basename not in batch_files:
                    batch_files[basename] = item
                else:
                    existing_ext = os.path.splitext(batch_files[basename].name)[1].lower()
                    if ext in ('.jpg', '.jpeg') and existing_ext in ('.tif', '.tiff'):
                        batch_files[basename] = item
            elif item.is_dir() and not item.name.startswith('.') and depth < 1:
                scan(item.path, depth + 1)

    scan(batch_dir, 0)
    return batch_files

def scan_sources():
    """Find every source image without processing anything.

    Returns (sources, unavailable_batches, complete):
      sources              image_id -> source/target info
      unavailable_batches  {(film_type, target_batch_name)} whose source could not be read
      complete             False if a whole source root is missing; orphan detection is
                           then unsafe (e.g. the NAS is not mounted)
    """
    sources = {}
    unavailable_batches = set()
    complete = True

    for film_type, source_dir in [('rollfilm', SOURCE_ROLLFILM), ('sheetfilm', SOURCE_SHEETFILM)]:
        if not os.path.isdir(source_dir):
            print(f"   ⚠ Source directory not found: {source_dir}")
            complete = False
            continue

        for entry in sorted(os.scandir(source_dir), key=lambda e: e.name):
            if not entry.is_symlink() or entry.name.startswith('.'):
                continue

            source_batch_name = entry.name
            target_batch_name = sanitize_filename(source_batch_name)
            source_batch_dir = os.path.realpath(entry.path)
            try:
                batch_files = find_batch_images(source_batch_dir)
            except Exception as e:
                # A broken symlink or unreadable batch must not make its images look deleted
                print(f"   ⚠ Cannot read batch {source_batch_name}: {e}")
                unavailable_batches.add((film_type, target_batch_name))
                continue

            target_batch_dir = os.path.join(TARGET_LIBRARY, film_type, target_batch_name)
            for basename, image_file in sorted(batch_files.items()):
                basename_clean = sanitize_filename(basename)
                image_dir = os.path.join(target_batch_dir, basename_clean)
                image_id = f"{film_type}/{target_batch_name}/{basename_clean}"
                sources[image_id] = {
                    'film_type': film_type,
                    'source_batch_name': source_batch_name,
                    'target_batch_name': target_batch_name,
                    'basename_clean': basename_clean,
                    'filename': image_file.name,
                    'source_path': image_file.path,
                    'small_output': os.path.join(image_dir, '600', f'{basename_clean}.jpg'),
                    'large_output': os.path.join(image_dir, '2560', f'{basename_clean}.jpg'),
                }

    return sources, unavailable_batches, complete

def process_sources(sources, index, force=False, dry_run=False):
    """Create/refresh the 600px and 2560px versions of changed source images."""
    stats = {'processed': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
    current_batch = None
    batch_stats = None

    def print_batch_summary():
        if batch_stats and (batch_stats['new'] or batch_stats['updated']):
            verb = 'would be ' if dry_run else ''
            print(f"      Summary: {batch_stats['new']} new, {batch_stats['updated']} updated {verb}"
                  f"(skipped {batch_stats['skipped']})")

    for image_id, src in sources.items():
        batch_key = (src['film_type'], src['source_batch_name'])
        if batch_key != current_batch:
            print_batch_summary()
            current_batch = batch_key
            batch_stats = {'new': 0, 'updated': 0, 'skipped': 0}
            print(f"\n   📂 {src['film_type']}/{src['source_batch_name']}")
            if src['source_batch_name'] != src['target_batch_name']:
                print(f"      → {src['target_batch_name']}")

        small_output, large_output = src['small_output'], src['large_output']
        small_needs = needs_update(src['source_path'], small_output, index, force)
        large_needs = needs_update(src['source_path'], large_output, index, force)

        if not small_needs and not large_needs:
            batch_stats['skipped'] += 1
            stats['skipped'] += 1
            continue

        is_update = os.path.exists(small_output) and os.path.exists(large_output)
        if is_update:
            print(f"      ↻ {src['filename']}")
            batch_stats['updated'] += 1
            stats['updated'] += 1
        else:
            print(f"      ✓ {src['filename']}")
            batch_stats['new'] += 1
            stats['processed'] += 1

        if dry_run:
            continue

        os.makedirs(os.path.dirname(small_output), exist_ok=True)
        os.makedirs(os.path.dirname(large_output), exist_ok=True)

        current_source = src['source_path']
        for needs, output, size in [(small_needs, small_output, SIZE_SMALL),
                                    (large_needs, large_output, SIZE_LARGE)]:
            if not needs:
                continue
            success = process_image(current_source, output, size)

            # If TIFF failed, try JPEG version if it exists
            if not success and current_source.lower().endswith(('.tif', '.tiff')):
                jpg_version = os.path.splitext(current_source)[0] + '.jpg'
                if os.path.exists(jpg_version):
                    print(f"      → Fallback to JPEG version")
                    success = process_image(jpg_version, output, size)
                    if success:
                        current_source = jpg_version

            if success:
                save_index_entry(index, current_source, output, get_file_signature(current_source))
            else:
                stats['errors'] += 1

    print_batch_summary()
    return stats

def scan_library():
    """Find all complete image pairs (600 + 2560) in the target library."""
    images_data = {}
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

                small_path = os.path.join(image_dir.path, '600', f'{image_dir.name}.jpg')
                large_path = os.path.join(image_dir.path, '2560', f'{image_dir.name}.jpg')
                if os.path.exists(small_path) and os.path.exists(large_path):
                    image_id = f"{film_type}/{batch_dir.name}/{image_dir.name}"
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
    return images_data

def remove_library_copy(image_id, index):
    """Delete an image's 600/2560 folder from the target library (never the source)."""
    parts = image_id.split('/')
    if len(parts) != 3 or any(p in ('', '.', '..') for p in parts):
        print(f"      ⚠ Refusing to remove unexpected path for {image_id}")
        return
    library_root = os.path.realpath(TARGET_LIBRARY)
    image_dir = os.path.realpath(os.path.join(TARGET_LIBRARY, *parts))
    if not image_dir.startswith(library_root + os.sep):
        print(f"      ⚠ Refusing to remove {image_dir}: outside {library_root}")
        return
    if os.path.isdir(image_dir):
        shutil.rmtree(image_dir)
        batch_dir = os.path.dirname(image_dir)
        if os.path.isdir(batch_dir) and not os.listdir(batch_dir):
            os.rmdir(batch_dir)

    # Forget index entries that pointed at the removed files
    for key in [k for k in index if k.split('|', 1)[1].startswith(image_dir + os.sep)]:
        del index[key]

# ============================================================================
# DATABASE: RENAMES, MERGES AND ORPHANS
# ============================================================================

def describe_metadata(meta):
    """Short description of user data attached to an image, e.g. '3 tags, description'."""
    if not meta:
        return ''
    parts = []
    if meta.get('tag_count'):
        parts.append(f"{meta['tag_count']} tag{'s' if meta['tag_count'] != 1 else ''}")
    if meta.get('has_description'):
        parts.append('description')
    if meta.get('favorite_count'):
        parts.append(f"favorite of {meta['favorite_count']}")
    return ', '.join(parts)

def load_db_images(conn, has_hash_column):
    """Load existing images with a summary of their user metadata."""
    with conn.cursor() as cur:
        hash_column = 'i.content_hash' if has_hash_column else 'NULL'
        cur.execute(f"""
            SELECT i.id, i.image_id, {hash_column},
                   COALESCE(i.description, '') <> '' AS has_description,
                   (SELECT COUNT(*) FROM image_tags it WHERE it.image_id = i.id) AS tag_count
            FROM images i;
        """)
        db_images = {
            row[1]: {'id': row[0], 'content_hash': row[2], 'has_description': row[3],
                     'tag_count': row[4], 'favorite_count': 0}
            for row in cur.fetchall()
        }

        cur.execute("SELECT to_regclass('public.favorites') IS NOT NULL;")
        has_favorites = cur.fetchone()[0]
        if has_favorites:
            cur.execute("""
                SELECT i.image_id, COUNT(*) FROM favorites f
                JOIN images i ON i.id = f.image_id GROUP BY i.image_id;
            """)
            for image_id, count in cur.fetchall():
                db_images[image_id]['favorite_count'] = count

    return db_images, has_favorites

def rename_db_image(cur, old_pk_id, image):
    """Point an existing row at the renamed image; tags and favorites follow the row id."""
    cur.execute("""
        UPDATE images
        SET image_id = %s, film_type = %s, batch_info = %s, filename_base = %s, film_stock = %s,
            thumbnail_path = %s, highres_path = %s
        WHERE id = %s;
    """, (image['image_id'], image['film_type'], image['batch_info'], image['filename_base'],
          image['film_stock'], translate_path_for_db(image['thumbnail_path']),
          translate_path_for_db(image['highres_path']), old_pk_id))

def merge_db_images(cur, old_pk_id, new_pk_id, has_favorites):
    """Move tags, favorites, description and reload flag from old_pk_id onto new_pk_id, then delete old_pk_id."""
    cur.execute("""
        INSERT INTO image_tags (image_id, tag_id)
        SELECT %s, tag_id FROM image_tags WHERE image_id = %s
        ON CONFLICT DO NOTHING;
    """, (new_pk_id, old_pk_id))
    if has_favorites:
        cur.execute("""
            INSERT INTO favorites (username, image_id, created_at)
            SELECT username, %s, created_at FROM favorites WHERE image_id = %s
            ON CONFLICT DO NOTHING;
        """, (new_pk_id, old_pk_id))
    cur.execute("""
        UPDATE images AS new
        SET description = CASE WHEN COALESCE(new.description, '') = '' THEN old.description ELSE new.description END,
            needs_reload = COALESCE(new.needs_reload, FALSE) OR COALESCE(old.needs_reload, FALSE)
        FROM images AS old
        WHERE new.id = %s AND old.id = %s;
    """, (new_pk_id, old_pk_id))
    cur.execute("DELETE FROM images WHERE id = %s;", (old_pk_id,))

def ensure_content_hash_column(conn):
    """Add images.content_hash if missing (same as add_content_hash.sql)."""
    with conn:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE images ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_images_content_hash ON images (content_hash);")

def has_content_hash_column(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'images' AND column_name = 'content_hash';
        """)
        return cur.fetchone() is not None

def fingerprint_for_dry_run(src, temp_dir):
    """Fingerprint a not-yet-processed source by rendering its 600px version to a temp file."""
    temp_output = os.path.join(temp_dir, f"{hashlib.sha1(src['source_path'].encode()).hexdigest()}.jpg")
    if process_image(src['source_path'], temp_output, SIZE_SMALL):
        return compute_content_hash(temp_output)
    return None

def find_renames(orphans, orphan_hashes, source_ids, source_hashes):
    """Pair each orphan with the single source image that has identical pixels.

    Returns (matches, ambiguous, unmatched); matches is a list of (orphan_id, target_id).
    """
    sources_by_hash = {}
    for image_id in source_ids:
        content_hash = source_hashes.get(image_id)
        if content_hash:
            sources_by_hash.setdefault(content_hash, []).append(image_id)

    matches, ambiguous, unmatched = [], [], []
    for orphan_id in sorted(orphans):
        targets = sources_by_hash.get(orphan_hashes.get(orphan_id), []) if orphan_hashes.get(orphan_id) else []
        if len(targets) == 1:
            matches.append((orphan_id, targets[0]))
        elif len(targets) > 1:
            ambiguous.append((orphan_id, targets))
        else:
            unmatched.append(orphan_id)
    return matches, ambiguous, unmatched

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

def reload_marked_images():
    """Reprocess only the images flagged with needs_reload in the database."""
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

    stats = {'updated': 0, 'errors': 0}
    images_to_reload = set(img_id for img_id, _, _ in marked_images)

    print("Reprocessing marked images...")
    print("-" * 70)

    for img_id, thumb_path, highres_path in marked_images:
        parts = img_id.split('/')
        if len(parts) < 3:
            continue
        film_type, batch_name, filename_base = parts[0], parts[1], parts[2]

        source_dir = SOURCE_ROLLFILM if film_type == 'rollfilm' else SOURCE_SHEETFILM

        # The source batch might have # or n, need to check both
        possible_batch_names = [batch_name, batch_name.replace('n', '#', 1)]

        source_batch_dir = None
        for entry in os.scandir(source_dir):
            if entry.is_symlink() and entry.name in possible_batch_names:
                source_batch_dir = os.path.realpath(entry.path)
                break

        if not source_batch_dir:
            print(f"   ⚠ Source batch not found for: {img_id}")
            stats['errors'] += 1
            continue

        source_file = None
        for basename, item in find_batch_images(source_batch_dir).items():
            if sanitize_filename(basename) == filename_base or basename == filename_base:
                source_file = item.path
                break

        if not source_file:
            print(f"   ⚠ Source file not found for: {img_id}")
            stats['errors'] += 1
            continue

        print(f"   🔄 {img_id}")
        target_thumb = thumb_path.replace(PATH_DATABASE, PATH_SCANNER)
        target_highres = highres_path.replace(PATH_DATABASE, PATH_SCANNER)
        if process_image(source_file, target_thumb, SIZE_SMALL):
            stats['updated'] += 1
        process_image(source_file, target_highres, SIZE_LARGE)

    if stats['updated'] > 0:
        clear_reload_flags(images_to_reload)

    print()
    print("-" * 70)
    print(f"Reload complete: {stats['updated']} images reprocessed, {stats['errors']} errors")
    return True

def process_all(skip_processing=False, force=False, dry_run=False, prune=False, allow_mass_prune=False):
    """Main function: process sources → scan library → update database."""

    print("=" * 70)
    print("ImageArchive Unified Update Script" + ("  [DRY RUN: nothing will be changed]" if dry_run else ""))
    print("=" * 70)
    print()

    print("[1/4] Loading processing index...")
    index = load_index()
    fingerprint_cache = load_fingerprint_cache()
    print(f"      Found {len(index)} tracked files")

    # ========================================================================
    # STEP 1: Scan and process source images
    # ========================================================================
    print()
    print("[2/4] Scanning source images...")
    print("-" * 70)
    sources, unavailable_batches, sources_complete = scan_sources()
    print(f"      Found {len(sources)} source images")

    if skip_processing:
        print("      Skipping image processing (--skip-processing)")
        stats = {'processed': 0, 'updated': 0, 'skipped': len(sources), 'errors': 0}
    else:
        stats = process_sources(sources, index, force=force, dry_run=dry_run)
        if not dry_run:
            write_index(index)

    print()
    print("-" * 70)
    verb = "would be " if dry_run else ""
    print(f"Image processing: {stats['processed']} new, {stats['updated']} updated {verb}"
          f"({stats['skipped']} unchanged, {stats['errors']} errors)")

    # ========================================================================
    # STEP 2: Scan library, extract EXIF and fingerprints
    # ========================================================================
    print()
    print("[3/4] Scanning library and extracting EXIF...")
    print("-" * 70)

    images_data = scan_library()

    def is_orphan(image_id):
        """True if the image's source file is gone (only decidable when all sources were readable)."""
        if not sources_complete or image_id in sources:
            return False
        film_type, batch_name = image_id.split('/')[:2]
        return (film_type, batch_name) not in unavailable_batches

    exif_count = 0
    for image_id, data in images_data.items():
        data['content_hash'] = get_content_hash(data['thumbnail_path'], fingerprint_cache)
        if is_orphan(image_id):
            continue  # stale copy; handled in step 4
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
    write_fingerprint_cache(fingerprint_cache)

    image_list = [data for image_id, data in images_data.items() if not is_orphan(image_id)]
    print(f"Found {len(image_list)} complete image pairs")
    print(f"Extracted EXIF from {exif_count} images")

    if not sources_complete:
        print("⚠ A source directory is missing: rename detection and orphan checks are disabled this run")

    if not dry_run:
        json_file = '../image_data.json'
        with open(json_file, 'w') as f:
            json.dump(image_list, f, indent=4, default=str)
        print(f"Saved to {json_file}")

    # ========================================================================
    # STEP 3: Update database
    # ========================================================================
    print()
    print("[4/4] Updating database..." if not dry_run else "[4/4] Checking database...")
    print("-" * 70)

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False

        if not dry_run:
            ensure_content_hash_column(conn)
        has_hash_column = has_content_hash_column(conn)
        db_images, has_favorites = load_db_images(conn, has_hash_column)

        # --- Renamed / deleted images -------------------------------------
        orphans = {image_id for image_id in set(db_images) | set(images_data) if is_orphan(image_id)}
        orphan_hashes = {}
        for orphan_id in orphans:
            library_copy = images_data.get(orphan_id)
            db_row = db_images.get(orphan_id)
            orphan_hashes[orphan_id] = ((library_copy or {}).get('content_hash')
                                        or (db_row or {}).get('content_hash'))

        source_hashes = {image_id: images_data[image_id]['content_hash']
                         for image_id in sources if image_id in images_data}
        if dry_run and any(orphan_hashes.values()):
            # New sources have no 600px version yet; render one to a temp file to compare
            unprocessed = [image_id for image_id in sources if not source_hashes.get(image_id)]
            if unprocessed:
                print(f"Fingerprinting {len(unprocessed)} unprocessed source images to detect renames...")
                with tempfile.TemporaryDirectory() as temp_dir:
                    for image_id in unprocessed:
                        source_hashes[image_id] = fingerprint_for_dry_run(sources[image_id], temp_dir)

        matches, ambiguous, unmatched = find_renames(orphans, orphan_hashes, sources, source_hashes)

        renamed, merged, stale_removed = [], [], []
        for orphan_id, target_id in matches:
            orphan_row = db_images.get(orphan_id)
            target_row = db_images.get(target_id)
            if orphan_row and target_id not in images_data and not dry_run:
                # The new version failed to process; keep the old row rather than point it at missing files
                print(f"   ⚠ Skipping {orphan_id} → {target_id}: new version has no library copy")
                continue

            if orphan_row and not target_row:
                renamed.append((orphan_id, target_id))
            elif orphan_row:
                merged.append((orphan_id, target_id))
            else:
                stale_removed.append((orphan_id, target_id))

            if not dry_run:
                with conn:
                    with conn.cursor() as cur:
                        if orphan_row and not target_row:
                            rename_db_image(cur, orphan_row['id'], images_data[target_id])
                        elif orphan_row:
                            merge_db_images(cur, orphan_row['id'], target_row['id'], has_favorites)
                remove_library_copy(orphan_id, index)

            # Track the result (also in dry runs) so a second old name for the same image becomes a merge
            if orphan_row:
                if not target_row:
                    db_images[target_id] = orphan_row
                db_images.pop(orphan_id, None)

        # --- Insert / update current images ---------------------------------
        db_stats = {'inserted': 0, 'updated': 0, 'errors': 0}
        if dry_run:
            db_stats['inserted'] = len([i for i in sources if i not in db_images])
        else:
            for image in image_list:
                try:
                    with conn:  # Each image in its own transaction
                        with conn.cursor() as cur:
                            image_id = image['image_id']
                            thumbnail_db = translate_path_for_db(image['thumbnail_path'])
                            highres_db = translate_path_for_db(image['highres_path'])

                            # Prepare EXIF JSON - remove null bytes that PostgreSQL can't handle
                            if image.get('exif_data'):
                                exif_json = json.dumps(image.get('exif_data', {}))
                                exif_json = exif_json.replace('\\u0000', '').replace('\x00', '')
                            else:
                                exif_json = None

                            cur.execute("SELECT id FROM images WHERE image_id = %s;", (image_id,))
                            if cur.fetchone():
                                cur.execute("""
                                    UPDATE images
                                    SET camera_make = %s, camera_model = %s, lens_model = %s,
                                        focal_length = %s, aperture = %s, shutter_speed = %s,
                                        iso = %s, date_taken = %s, exif_data = %s::jsonb,
                                        thumbnail_path = %s, highres_path = %s, content_hash = %s
                                    WHERE image_id = %s;
                                """, (
                                    image.get('camera_make', ''), image.get('camera_model', ''),
                                    image.get('lens_model', ''), image.get('focal_length', ''),
                                    image.get('aperture', ''), image.get('shutter_speed', ''),
                                    image.get('iso', ''), image.get('date_taken'), exif_json,
                                    thumbnail_db, highres_db, image.get('content_hash'), image_id
                                ))
                                db_stats['updated'] += 1
                            else:
                                cur.execute("""
                                    INSERT INTO images
                                    (image_id, film_type, batch_info, filename_base, film_stock,
                                     thumbnail_path, highres_path, description,
                                     camera_make, camera_model, lens_model, focal_length,
                                     aperture, shutter_speed, iso, date_taken, exif_data, content_hash)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s);
                                """, (
                                    image_id, image['film_type'], image['batch_info'],
                                    image['filename_base'], image['film_stock'],
                                    thumbnail_db, highres_db, image.get('description', ''),
                                    image.get('camera_make', ''), image.get('camera_model', ''),
                                    image.get('lens_model', ''), image.get('focal_length', ''),
                                    image.get('aperture', ''), image.get('shutter_speed', ''),
                                    image.get('iso', ''), image.get('date_taken'), exif_json,
                                    image.get('content_hash')
                                ))
                                db_stats['inserted'] += 1
                except Exception as e:
                    # Transaction rolls back automatically; continue with next image
                    print(f"   ✗ Error: {image.get('image_id', 'unknown')}: {e}")
                    db_stats['errors'] += 1

        # --- Report renames and orphans -------------------------------------
        def print_list(title, items, formatter, limit=25):
            if not items:
                return
            print(f"\n{title} ({len(items)}):")
            for item in items[:limit]:
                print(f"   {formatter(item)}")
            if len(items) > limit:
                print(f"   ... and {len(items) - limit} more")

        would = "would be " if dry_run else ""
        meta_suffix = lambda image_id: (f"  [{describe_metadata(db_images.get(image_id))}]"
                                        if describe_metadata(db_images.get(image_id)) else "")
        print_list(f"Renamed images {would}moved to their new name (tags/description/favorites kept)", renamed,
                   lambda r: f"{r[0]} → {r[1]}")
        print_list(f"Earlier duplicates {would}merged into the current image", merged,
                   lambda r: f"{r[0]} → {r[1]}")
        print_list(f"Stale library copies {would}removed", stale_removed, lambda r: f"{r[0]} (now {r[1]})")
        print_list("Possible renames with several identical candidates (left alone)", ambiguous,
                   lambda a: f"{a[0]} → {', '.join(a[1])}")
        print_list("Orphaned images (source file no longer exists)", unmatched,
                   lambda image_id: f"{image_id}{meta_suffix(image_id)}"
                                    f"{'' if image_id in db_images else '  [library copy only]'}")

        # --- Prune orphans ---------------------------------------------------
        if unmatched and prune:
            with_metadata = [i for i in unmatched if describe_metadata(db_images.get(i))]
            limit = max(1, int(len(db_images) * PRUNE_MAX_FRACTION))
            if not sources_complete:
                print("\n⚠ Not pruning: a source directory is missing")
            elif len(unmatched) > limit and not allow_mass_prune:
                print(f"\n⚠ Not pruning: {len(unmatched)} orphans is more than {int(PRUNE_MAX_FRACTION * 100)}% "
                      f"of the library. Check the source mounts, then re-run with --allow-mass-prune.")
            elif dry_run:
                print(f"\n--prune would delete {len(unmatched)} orphaned images "
                      f"({len(with_metadata)} of them have tags, descriptions or favorites)")
            else:
                for orphan_id in unmatched:
                    row = db_images.get(orphan_id)
                    if row:
                        with conn:
                            with conn.cursor() as cur:
                                cur.execute("DELETE FROM images WHERE id = %s;", (row['id'],))
                    remove_library_copy(orphan_id, index)
                print(f"\n🗑 Pruned {len(unmatched)} orphaned images "
                      f"({len(with_metadata)} had tags, descriptions or favorites)")
        elif unmatched:
            print("   → Review the list, then run with --prune to delete them (try --dry-run --prune first)")

        if not dry_run:
            write_index(index)

        if dry_run:
            print(f"\nDatabase: {db_stats['inserted']} new images would be added")
        else:
            print(f"\nDatabase updated: {db_stats['inserted']} new, {db_stats['updated']} updated, "
                  f"{db_stats['errors']} errors")

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
    print("✓ Dry run complete (nothing was changed)" if dry_run else "✓ Update Complete!")
    print("=" * 70)
    print(f"Images processed:  {stats['processed']}")
    print(f"Images updated:    {stats['updated']}")
    print(f"Images skipped:    {stats['skipped']}")
    print(f"Renamed/merged:    {len(renamed) + len(merged)}")
    print(f"Orphaned:          {len(unmatched)}")
    print(f"Errors:            {stats['errors']}")
    print()

    return True

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Unified ImageArchive update script')
    parser.add_argument('--skip-processing', action='store_true',
                        help='Skip image processing, only scan and update database')
    parser.add_argument('--reload-marked', action='store_true',
                        help='Only reload images marked with needs_reload flag')
    parser.add_argument('--force', action='store_true',
                        help='Re-process every source image, even if unchanged')
    parser.add_argument('--dry-run', action='store_true',
                        help='Report new, changed, renamed and orphaned images without changing anything')
    parser.add_argument('--prune', action='store_true',
                        help='Delete orphaned images (source file gone, no rename match) from the database and library')
    parser.add_argument('--allow-mass-prune', action='store_true',
                        help=f'Allow --prune to delete more than {int(PRUNE_MAX_FRACTION * 100)}%% of the library')

    args = parser.parse_args()

    start_time = time.time()

    if args.reload_marked:
        ok = reload_marked_images()
    else:
        ok = process_all(skip_processing=args.skip_processing, force=args.force, dry_run=args.dry_run,
                         prune=args.prune, allow_mass_prune=args.allow_mass_prune)
    if not ok:
        sys.exit(1)

    elapsed = time.time() - start_time
    print(f"Total time: {elapsed:.1f}s")
