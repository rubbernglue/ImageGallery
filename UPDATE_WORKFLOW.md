# Complete Update Workflow

## Overview

This document explains the complete process for adding new images or updating existing images with EXIF data.

## Prerequisites

```bash
# Install required packages
pip install Pillow
sudo apt-get install libimage-exiftool-perl
```

## Step-by-Step Workflow

### Adding New Images (Fresh Batch)

Example: You scanned a new roll "645_2025_Nikon_med_Ilford"

```bash
# 1. Add symlink to source directory
ln -s /path/to/scans/645_2025_Nikon_med_Ilford /mnt/omv/Photo/Collected/Rollfilm/

# 2. Process images (creates 600px and 2560px with EXIF)
./process_scaled_library.sh

# Expected output:
#   📁 Directory: 645_2025_Nikon_med_Ilford
#   ✓ Processing: image_001.tif
#   ✓ Processing: image_002.tif
#   Summary: 24 new, 0 updated, 0 skipped

# 3. Scan images and extract EXIF to JSON
python library_scanner.py

# Expected output:
#   Extracting EXIF from: rollfilm/645_2025_Nikon_med_Ilford/image_001
#   Found 24 unique image pairs
#   Extracted EXIF from 24 images
#   Successfully generated image_data.json

# 4. Update database
python update_database.py

# Expected output:
#   Processing 8988 images from image_data.json
#   Inserted: rollfilm/645_2025_Nikon_med_Ilford/image_001
#   New images inserted: 24

# Done! Images are now in the database with EXIF
```

### Updating EXIF on Existing Images

Example: You added EXIF metadata to source TIFFs that were already scanned

```bash
# 1. Update EXIF in your source TIFF files
#    (using your preferred EXIF editor)

# 2. Re-process (detects EXIF changes automatically)
./process_scaled_library.sh

# Expected output:
#   📁 Directory: 645_2025_Nikon_med_Ilford
#   ↻ Updating: image_001.tif (EXIF or content changed)
#   ↻ Updating: image_002.tif (EXIF or content changed)
#   Summary: 0 new, 24 updated, 0 skipped

# 3. Re-scan to get updated EXIF
python library_scanner.py

# 4. Re-run update (overwrites EXIF in database)
python update_database.py

# Done! EXIF updated in database
```

### Adding Images to Existing Batch

Example: You added 5 more images to an existing directory

```bash
# 1. Add new TIFF files to source directory

# 2. Process (only processes new files)
./process_scaled_library.sh

# Expected output:
#   📁 Directory: 645_2025_Nikon_med_Ilford
#   ✓ Processing: image_025.tif
#   ✓ Processing: image_026.tif
#   Summary: 5 new, 0 updated, 24 skipped

# 3. Scan and update
python library_scanner.py
python update_database.py

# Done! New images added
```

## Recovery from Errors

### Clean Up Failed Processing

If `process_scaled_library.sh` was interrupted or failed:

```bash
# 1. The script auto-cleans on next run, or manually:
find /mnt/omv/Photo/Picture_library -name "*.tmp*.jpg" -delete

# 2. Re-run
./process_scaled_library.sh
```

The script will:
- Skip completed files
- Process incomplete files
- Show which files need processing

### JSON Serialization Errors

If `library_scanner.py` fails with "not JSON serializable":

**This is now fixed** in the updated version, but if you still see it:

```bash
# Check which image is causing the issue
python library_scanner.py 2>&1 | grep -A 5 "Error"

# The script will skip problematic images and continue
```

The updated script:
- Converts IFDRational to float
- Converts bytes to strings
- Handles all PIL EXIF types
- Falls back to basic serialization if needed

### Database Connection Errors

If `update_database.py` fails:

```bash
# 1. Check database is running
pg_isready -h localhost -p 5432

# 2. Check credentials in update_database.py match your setup

# 3. Test connection
psql -U postgres -d imagearchive -c "SELECT COUNT(*) FROM images;"
```

## Quick Reference

| Task | Commands |
|------|----------|
| **Add new batch** | `./process_scaled_library.sh` → `python library_scanner.py` → `python update_database.py` |
| **Update EXIF** | Same as above |
| **Update specific batch** | `python update_database.py --scan-dir /opt/media/rollfilm batch_name` |
| **Clean temp files** | `find /mnt/omv/Photo/Picture_library -name "*.tmp*.jpg" -delete` |
| **Check progress** | Script shows: new/updated/skipped counts |

## Performance Tips

1. **Incremental updates are fast**: Script only processes what changed
2. **First run is slow**: Processing 8000+ images takes time
3. **Subsequent runs are fast**: Only new/changed files processed

**Typical times:**
- First full scan: 2-4 hours (8000 images)
- Adding 24 new images: 2-3 minutes
- Updating EXIF on 24 images: 1-2 minutes
- Running with no changes: 10-20 seconds

## Verification

After updating, verify everything worked:

```bash
# 1. Check JSON file exists and has EXIF
jq '.[0] | .camera_model' image_data.json

# 2. Check database has EXIF
psql -U postgres -d imagearchive -c "SELECT image_id, camera_model, lens_model FROM images WHERE camera_model IS NOT NULL LIMIT 5;"

# 3. Open website and check an image
#    - Should show "Camera & Settings" section
#    - Should be searchable by camera name
```

## Complete Example Session

```bash
# Scenario: Adding new batch with EXIF

$ ln -s /scans/new_batch /mnt/omv/Photo/Collected/Rollfilm/

$ ./process_scaled_library.sh
Processing: rollfilm
📁 Directory: new_batch
   ✓ Processing: scan001.tif
   ✓ Processing: scan002.tif
   ...
   Summary: 24 new, 0 updated, 0 skipped
🎉 Complete! 24 new images

$ python library_scanner.py
Scanning directory: /opt/media
  Extracting EXIF from: rollfilm/new_batch/scan001
  ...
Found 9012 unique image pairs
Extracted EXIF from 8733 images
Successfully generated image_data.json

$ python update_database.py
Processing 9012 images from image_data.json
  Inserted: rollfilm/new_batch/scan001
  ...
New images inserted: 24
✓ Database update completed successfully!

# Done! New images with EXIF now in database
```

## Maintenance

### Regular Updates

When adding images regularly:

```bash
#!/bin/bash
# save as: update_archive.sh

echo "Updating film archive..."

# Process any new/changed images
./process_scaled_library.sh

# Scan for EXIF
python library_scanner.py

# Update database
python update_database.py

echo "✓ Archive updated!"
```

Make it executable: `chmod +x update_archive.sh`

Then just run: `./update_archive.sh` whenever you add images!

