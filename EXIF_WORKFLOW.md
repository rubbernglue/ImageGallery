# EXIF Data Workflow Guide

## Overview

Your ImageArchive now fully supports EXIF data extraction, storage, display, and search. This guide explains the complete workflow for processing images with EXIF preservation.

## Prerequisites

### Install Required Tools

```bash
# Python Pillow library for EXIF extraction
pip install Pillow

# ExifTool for perfect EXIF preservation (highly recommended)
sudo apt-get install libimage-exiftool-perl
```

### Update Database Schema

```bash
# Add EXIF columns to your database
psql -U postgres -d imagearchive -f database_schema_exif.sql
```

This adds columns for:
- Camera make/model
- Lens information
- Focal length, aperture, shutter speed, ISO
- Date taken
- Full EXIF data as JSON

## Complete Workflow

### Step 1: Process Source Images

Your updated `process_scaled_library.sh` script now:
- ✅ Preserves ALL EXIF data when creating scaled versions
- ✅ Detects when EXIF data changes in source images
- ✅ Re-processes only changed files
- ✅ Uses exiftool for perfect EXIF preservation (if installed)
- ✅ Falls back to ImageMagick if exiftool unavailable

**Run the script:**
```bash
./process_scaled_library.sh
```

**What it does:**
```
📁 Scans /mnt/omv/Photo/Collected/Rollfilm
📁 Scans /mnt/omv/Photo/Collected/Sheetfilm
📸 Creates 600px thumbnails with EXIF
📸 Creates 2560px high-res with EXIF
✓ Skips unchanged files
↻ Updates files with changed EXIF
```

**Output structure:**
```
/mnt/omv/Photo/Picture_library/
├── rollfilm/
│   └── 645_2025_Nikon_med_Ilford/
│       └── image_001/
│           ├── 600/image_001.jpg    (with EXIF)
│           └── 2560/image_001.jpg   (with EXIF)
└── sheetfilm/
    └── 5x7_batch/
        └── image_002/
            ├── 600/image_002.jpg
            └── 2560/image_002.jpg
```

### Step 2: Scan and Extract EXIF

The updated `library_scanner.py` extracts EXIF from 2560px images:

```bash
python library_scanner.py
```

**What it extracts:**
- Camera make (Canon, Nikon, etc.)
- Camera model (EOS 5D, D850, etc.)
- Lens model
- Focal length (50mm, 24-70mm, etc.)
- Aperture (f/2.8, f/8, etc.)
- Shutter speed (1/1000, 1", etc.)
- ISO (100, 400, 3200, etc.)
- Date/time taken
- Full EXIF as JSON

**Output:** `image_data.json` with EXIF data

### Step 3: Update Database

```bash
python update_database.py
```

This:
- Adds new images to database with EXIF
- Skips existing images
- Preserves tags and descriptions

**Or update specific batch:**
```bash
python update_database.py --scan-dir /opt/media/rollfilm 645_2025_Nikon_med_Ilford
```

### Step 4: View and Search

Open your website - EXIF data is now:
- ✅ Displayed in image modal
- ✅ Searchable in the search box
- ✅ Automatically shown if available

## Usage Scenarios

### Scenario 1: Adding New Images

You have new scans to add:

```bash
# 1. Add source images to /mnt/omv/Photo/Collected/Rollfilm or Sheetfilm
# 2. Process them:
./process_scaled_library.sh

# 3. Scan and update:
python library_scanner.py
python update_database.py
```

### Scenario 2: Updating EXIF on Existing Images

You've added EXIF data to source images that were already processed:

```bash
# 1. Update EXIF in source files using your preferred tool
# 2. Re-process (script detects EXIF changes):
./process_scaled_library.sh

# 3. Re-scan and update database:
python library_scanner.py
python update_database.py
```

The script will:
- Detect that EXIF has changed
- Re-process only affected files
- Update database with new EXIF

### Scenario 3: Force Re-process Everything

If you want to re-extract EXIF from all images:

```bash
# 1. Delete scaled versions:
rm -rf /mnt/omv/Photo/Picture_library/rollfilm/*/*/600/*.jpg
rm -rf /mnt/omv/Photo/Picture_library/rollfilm/*/*/2560/*.jpg
# (Repeat for sheetfilm)

# 2. Re-process all:
./process_scaled_library.sh

# 3. Re-scan:
python library_scanner.py
python update_database.py
```

## EXIF Features

### Display in Modal

When viewing an image, if EXIF data exists, you'll see:

```
Camera & Settings
──────────────────────────────
Camera:         Canon EOS 5D Mark III
Lens:          Canon EF 50mm f/1.4 USM
Focal Length:  50mm
Aperture:      f/2.8
Shutter:       1/1000
ISO:           400

Date Taken: 2024-12-15 14:23:45
```

### Search by EXIF

Search examples:
- `Canon` - finds all Canon images
- `Nikon D850` - finds specific camera
- `f/1.4` - finds images shot at f/1.4
- `50mm` - finds 50mm focal length
- `3200` - finds ISO 3200 images

## Script Features Explained

### EXIF Preservation Methods

**With exiftool (recommended):**
```bash
# Step 1: Resize image
magick source.jpg -resize 2560x2560 output.jpg

# Step 2: Copy ALL EXIF from source to output
exiftool -TagsFromFile source.jpg -all:all output.jpg
```

**Without exiftool (fallback):**
```bash
# ImageMagick preserves most EXIF automatically
magick source.jpg -resize 2560x2560 -quality 85 output.jpg
```

### Change Detection

The script checks:
1. File modification time
2. EXIF data checksum (if exiftool available)

If either changed → re-process file

### Directory Structure

**Expected source:**
```
/mnt/omv/Photo/Collected/
├── Rollfilm/
│   └── [symlinks to batches]
└── Sheetfilm/
    └── [symlinks to batches]
```

**Generated output:**
```
/mnt/omv/Photo/Picture_library/
├── rollfilm/
│   └── batch_name/
│       └── image_name/
│           ├── 600/image_name.jpg
│           └── 2560/image_name.jpg
└── sheetfilm/
    └── batch_name/
        └── image_name/
            ├── 600/image_name.jpg
            └── 2560/image_name.jpg
```

## Troubleshooting

### EXIF not showing up

**Check:**
```bash
# 1. Verify source has EXIF:
exiftool /path/to/source/image.tif

# 2. Verify scaled version has EXIF:
exiftool /mnt/omv/Photo/Picture_library/rollfilm/.../2560/image.jpg

# 3. Check database:
psql -U postgres -d imagearchive -c "SELECT camera_model, lens_model FROM images WHERE image_id = 'your/image/id';"
```

### Script says "exiftool not found"

**Install it:**
```bash
sudo apt-get install libimage-exiftool-perl
```

Without exiftool, the script still works but EXIF preservation may be incomplete.

### Re-scan specific batch

If you updated EXIF for one batch only:

```bash
# 1. Process just that batch's directory
./process_scaled_library.sh  # Will detect changes automatically

# 2. Update database for that batch
python update_database.py --scan-dir /opt/media/rollfilm batch_name
```

## Performance

**Script optimizations:**
- Skips files that haven't changed
- Only checks EXIF if exiftool available
- Processes in batches
- Shows progress for each directory

**Typical speeds:**
- New file processing: ~2-5 seconds per image
- EXIF-only update: ~1-2 seconds per image
- Skip (no change): Instant

## Best Practices

1. **Always use exiftool** for EXIF preservation
2. **Run incrementally** - script handles updates efficiently
3. **Check logs** - script shows what was updated vs skipped
4. **Verify EXIF** - spot-check a few images after processing
5. **Backup source** - always keep original TIFFs with EXIF

## Complete Example

Starting fresh with new batch:

```bash
# 1. Add new batch symlink
ln -s /path/to/scans/645_batch_050 /mnt/omv/Photo/Collected/Rollfilm/

# 2. Process (creates scaled versions with EXIF)
./process_scaled_library.sh
# Output: ✓ Processing 645_batch_050... 24 new files

# 3. Extract EXIF to JSON
python library_scanner.py
# Output: Extracting EXIF from: rollfilm/645_batch_050/...
#         Found 24 unique image pairs
#         Extracted EXIF from 24 images

# 4. Update database
python update_database.py
# Output: New images inserted: 24

# 5. Done! View on website
# - Images appear in gallery
# - EXIF data shown in modal
# - Searchable by camera/lens/settings
```

## Summary

Your complete workflow is now:
1. **Add/update source images** → EXIF in TIFFs
2. **Run script** → Scaled images with EXIF preserved
3. **Scan** → Extract EXIF to JSON
4. **Update database** → EXIF stored in PostgreSQL
5. **View/search** → EXIF displayed and searchable

All steps handle updates intelligently - only processing what changed!

## Common Issues and Solutions

### Issue: "cannot stat .tmp.jpg: No such file or directory"

**Cause:** Multi-page TIFF files create multiple output files with frame numbers

**Solution:** Updated script now:
- Uses `[0]` to process only first frame/page
- Cleans up temp files automatically
- Handles multi-page TIFFs correctly

**Fix existing files:**
```bash
# Clean up temp files
find /mnt/omv/Photo/Picture_library -name "*.tmp*.jpg" -delete

# Re-run the script
./process_scaled_library.sh
```

### Issue: "Wrong data type for PixelXDimension" warnings

**Cause:** TIFF files with non-standard EXIF tags

**Solution:** These are warnings, not errors. The script now:
- Suppresses these warnings (they're harmless)
- Uses `-quiet` flag to reduce noise
- Still processes images correctly

**These warnings are safe to ignore** - the images are processed fine.

### Issue: Files not updating when EXIF changes

**Check if exiftool is installed:**
```bash
which exiftool
# Should output: /usr/bin/exiftool

# If not found, install:
sudo apt-get install libimage-exiftool-perl
```

Without exiftool, the script can't detect EXIF-only changes.

### Issue: Script is slow

**Optimization tips:**

1. **Skip unchanged files** (already automatic)
2. **Process specific directories only**
3. **Use SSD for TARGET_LIBRARY if possible**

**Benchmarks:**
- 100 images, all new: ~5-10 minutes
- 100 images, EXIF update: ~2-3 minutes
- 100 images, no changes: ~5-10 seconds

### Issue: Some images missing EXIF in database

**Debug steps:**

```bash
# 1. Check if EXIF exists in scaled image
exiftool /mnt/omv/Photo/Picture_library/rollfilm/.../2560/image.jpg | grep -i camera

# 2. Check if Python can read it
python3 << 'PYTHON'
from PIL import Image
img = Image.open('/path/to/image.jpg')
exif = img._getexif()
print(f"EXIF found: {exif is not None}")
PYTHON

# 3. Re-scan specific batch
python update_database.py --scan-dir /opt/media/rollfilm batch_name
```

### Recovering from Failed Run

If script was interrupted or failed:

```bash
# 1. Clean up temp files
find /mnt/omv/Photo/Picture_library -name "*.tmp*.jpg" -delete

# 2. Check for incomplete directories
find /mnt/omv/Photo/Picture_library -type d -name "600" -o -name "2560" | while read dir; do
    if [ -z "$(ls -A $dir)" ]; then
        echo "Empty: $dir"
    fi
done

# 3. Re-run script (will process missing files)
./process_scaled_library.sh
```

The script will automatically:
- Skip completed files
- Process incomplete files
- Clean up temp files

