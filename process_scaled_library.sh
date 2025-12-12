#!/bin/bash

# ============================================================================
# Film Archive Image Processing Script with EXIF Preservation
# ============================================================================
# This script:
# 1. Processes source images from rollfilm and sheetfilm directories
# 2. Creates scaled versions (600px and 2560px) with EXIF data preserved
# 3. Handles updates: re-processes if source EXIF has changed
# 4. Skips files that are already up-to-date
# ============================================================================

SOURCE_ROLLFILM="/mnt/omv/Photo/Collected/Rollfilm"
SOURCE_SHEETFILM="/mnt/omv/Photo/Collected/Sheetfilm"
TARGET_LIBRARY="/mnt/omv/Photo/Picture_library"

# Index file for tracking processed images (speeds up subsequent runs)
INDEX_FILE="$TARGET_LIBRARY/.processing_index"

# Define output sizes
SIZE_SMALL="600x600>"   # Max width/height 600px, only scale down
SIZE_LARGE="2560x2560>" # Max width/height 2560px, only scale down

# VIPS threshold (in megapixels) - if image is larger, use VIPS instead
VIPS_THRESHOLD_MP=80 # in megapixels

# Statistics
TOTAL_PROCESSED=0
TOTAL_SKIPPED=0
TOTAL_UPDATED=0
TOTAL_ERRORS=0

# ---------------------
# Check dependencies
# ---------------------

if ! command -v magick &> /dev/null && ! command -v convert &> /dev/null; then
    echo "Error: ImageMagick 'magick' or 'convert' command not found. Please install ImageMagick."
    exit 1
fi

if ! command -v identify &> /dev/null; then
    echo "Error: ImageMagick 'identify' command not found. Please install ImageMagick."
    exit 1
fi

if ! command -v exiftool &> /dev/null; then
    echo "Warning: 'exiftool' not found. EXIF data will not be preserved optimally."
    echo "Install with: sudo apt-get install libimage-exiftool-perl"
    echo "Continuing with ImageMagick EXIF preservation (may be incomplete)..."
    USE_EXIFTOOL=false
else
    USE_EXIFTOOL=true
    echo "✓ Found exiftool - will preserve full EXIF data"
fi

echo "Starting image processing and scaled library creation..."
echo "============================================================"

# Initialize or load index file
touch "$INDEX_FILE"
echo "Using index file: $INDEX_FILE ($(wc -l < "$INDEX_FILE") entries)"

# Clean up any leftover temp files from previous failed runs
echo "Cleaning up temporary files..."
TEMP_COUNT=$(find "$TARGET_LIBRARY" -name "*.tmp.jpg" -o -name "*.tmp-*.jpg" 2>/dev/null | wc -l)
if [ "$TEMP_COUNT" -gt 0 ]; then
    find "$TARGET_LIBRARY" -name "*.tmp.jpg" -o -name "*.tmp-*.jpg" 2>/dev/null | while read -r tmpfile; do
        rm -f "$tmpfile"
    done
    echo "✓ Cleaned $TEMP_COUNT temp files"
else
    echo "✓ No temp files to clean"
fi
echo ""

EXCLUDE_PATHS_ARR=(
    -path '*/@eaDir*'
    -o -name 'part_*.jpg'
    -o -name '._*'
)

# Allowed Extensions array
ALLOWED_EXTENSIONS_ARR=(
    -name '*.jpg'
    -o -name '*.jpeg'
    -o -name '*.tif'
    -o -name '*.tiff'
)

# ============================================================================
# Function: Get file signature for index (mtime + size)
# ============================================================================
get_file_signature() {
    local file="$1"
    stat -c "%Y:%s" "$file" 2>/dev/null || echo "0:0"
}

# ============================================================================
# Function: Check if source image needs update using index
# ============================================================================
needs_update() {
    local source_file="$1"
    local target_file="$2"
    
    # If target doesn't exist, needs processing
    if [ ! -f "$target_file" ]; then
        return 0 # true - needs update
    fi
    
    # Quick check using index file (much faster than exiftool)
    local source_sig=$(get_file_signature "$source_file")
    local index_key="${source_file}|${target_file}"
    
    if [ -f "$INDEX_FILE" ]; then
        # Check if this file pair is in the index with same signature
        if grep -q "^${index_key}|${source_sig}$" "$INDEX_FILE" 2>/dev/null; then
            return 1 # false - no update needed (index says it's current)
        fi
    fi
    
    # If source is newer than target, needs update
    if [ "$source_file" -nt "$target_file" ]; then
        return 0 # true - needs update
    fi
    
    # Optional: Deep EXIF check only if index says might be different
    # This is slower but catches EXIF-only changes
    if $USE_EXIFTOOL && [ -n "${DEEP_EXIF_CHECK:-}" ]; then
        local source_exif=$(exiftool -Make -Model -LensModel -ISO -FNumber -ExposureTime -FocalLength -DateTimeOriginal "$source_file" 2>/dev/null | md5sum | cut -d' ' -f1)
        local target_exif=$(exiftool -Make -Model -LensModel -ISO -FNumber -ExposureTime -FocalLength -DateTimeOriginal "$target_file" 2>/dev/null | md5sum | cut -d' ' -f1)
        
        if [ "$source_exif" != "$target_exif" ]; then
            return 0 # true - EXIF changed, needs update
        fi
    fi
    
    return 1 # false - no update needed
}

# ============================================================================
# Function: Update index with processed file
# ============================================================================
update_index() {
    local source_file="$1"
    local target_file="$2"
    local source_sig=$(get_file_signature "$source_file")
    local index_key="${source_file}|${target_file}"
    
    # Remove old entry if exists
    if [ -f "$INDEX_FILE" ]; then
        sed -i "/^$(echo "$index_key" | sed 's/[\/&]/\\&/g')|/d" "$INDEX_FILE" 2>/dev/null || true
    fi
    
    # Add new entry
    echo "${index_key}|${source_sig}" >> "$INDEX_FILE"
}

# ============================================================================
# Function: Process a single image with EXIF preservation
# ============================================================================
process_image() {
    local image_path="$1"
    local output_path="$2"
    local size="$3"
    
    # Create temp filename
    local temp_file="${output_path}.tmp.jpg"
    
    if $USE_EXIFTOOL; then
        # Method 1: Use exiftool for perfect EXIF preservation
        
        # First, resize with ImageMagick
        # Use [0] to only process first frame/page of multi-page TIFFs
        # Suppress TIFF warnings with -quiet
        magick "${image_path}[0]" -quiet -auto-orient -resize "$size" -quality 85 "$temp_file" 2>&1 | grep -v "Wrong data type" | grep -v "tag ignored" || true
        
        # Check if resize was successful
        if [ ! -f "$temp_file" ]; then
            echo "      ERROR: Failed to create resized image"
            return 1
        fi
        
        # Then copy ALL EXIF data from source to resized image
        # Suppress warnings about TIFF data types
        exiftool -TagsFromFile "$image_path" -all:all -overwrite_original "$temp_file" 2>/dev/null
        
        # Move to final location
        mv "$temp_file" "$output_path"
        
    else
        # Method 2: Use ImageMagick's built-in EXIF handling (preserves most EXIF)
        
        # Process first frame only with [0], preserve EXIF profiles
        # Suppress TIFF warnings
        magick "${image_path}[0]" -quiet -auto-orient -resize "$size" -quality 85 "$output_path" 2>&1 | grep -v "Wrong data type" | grep -v "tag ignored" || true
        
        if [ ! -f "$output_path" ]; then
            echo "      ERROR: Failed to create resized image"
            return 1
        fi
    fi
    
    # Clean up any stray temp files (in case of multi-page TIFF issues)
    rm -f "${output_path}.tmp-"*.jpg
    
    return 0
}

# ============================================================================
# Function: Process source directory type (rollfilm or sheetfilm)
# ============================================================================
process_source_type() {
    local SOURCE_DIR="$1"
    local TARGET_SUBDIR="$2"
    
    echo ""
    echo "════════════════════════════════════════════════════════"
    echo "Processing: $TARGET_SUBDIR"
    echo "════════════════════════════════════════════════════════"
    
    local dir_processed=0
    local dir_skipped=0
    local dir_updated=0
    
    # Find all symlinks (directories) in source
    find "$SOURCE_DIR" -maxdepth 1 -mindepth 1 -type l -not -name '.*' -print0 | while IFS= read -r -d $'\0' roll_link; do
        
        roll_dir=$(readlink -f "$roll_link") 
        if [ -z "$roll_dir" ]; then
            echo "⚠ Warning: Could not resolve symlink $roll_link. Skipping."
            ((TOTAL_ERRORS++))
            continue
        fi

        SOURCE_DIR_NAME=$(basename "$roll_link")
        # Replace spaces with underscores in directory name
        TARGET_DIR_NAME="${SOURCE_DIR_NAME// /_}"
        TARGET_DEST="$TARGET_LIBRARY/$TARGET_SUBDIR/$TARGET_DIR_NAME"
        
        mkdir -p "$TARGET_DEST" 
        
        echo ""
        echo "📁 Directory: $SOURCE_DIR_NAME → $TARGET_DIR_NAME"
        echo "   Source: $roll_dir"
        
        local batch_processed=0
        local batch_skipped=0
        local batch_updated=0

        # Find all images in the source directory
        find "$roll_dir" -maxdepth 1 -type f \( "${ALLOWED_EXTENSIONS_ARR[@]}" \) -not \( "${EXCLUDE_PATHS_ARR[@]}" \) -print0 | while IFS= read -r -d $'\0' image_path; do
            
            FILENAME=$(basename "$image_path")
            BASENAME="${FILENAME%.*}"
            # Replace spaces with underscores in filename
            BASENAME_CLEAN="${BASENAME// /_}"
            
            PICTURE_DIR="$TARGET_DEST/$BASENAME_CLEAN"
            SMALL_OUTPUT="$PICTURE_DIR/600/$BASENAME_CLEAN.jpg"
            LARGE_OUTPUT="$PICTURE_DIR/2560/$BASENAME_CLEAN.jpg"
            
            # Create the destination structure
            mkdir -p "$PICTURE_DIR/600"
            mkdir -p "$PICTURE_DIR/2560"
            
            # Check if both files exist and are up-to-date
            small_needs_update=$(needs_update "$image_path" "$SMALL_OUTPUT" && echo "yes" || echo "no")
            large_needs_update=$(needs_update "$image_path" "$LARGE_OUTPUT" && echo "yes" || echo "no")
            
            if [ "$small_needs_update" = "no" ] && [ "$large_needs_update" = "no" ]; then
                # Both files exist and are current
                ((batch_skipped++))
                continue
            fi
            
            if [ -f "$SMALL_OUTPUT" ] && [ -f "$LARGE_OUTPUT" ]; then
                echo "   ↻ Updating: $FILENAME (EXIF or content changed)"
                ((batch_updated++))
            else
                echo "   ✓ Processing: $FILENAME"
                ((batch_processed++))
            fi
            
            # Process 600px version if needed
            if [ "$small_needs_update" = "yes" ]; then
                if process_image "$image_path" "$SMALL_OUTPUT" "$SIZE_SMALL"; then
                    update_index "$image_path" "$SMALL_OUTPUT"
                else
                    echo "      FAILED to process 600px version"
                    ((TOTAL_ERRORS++))
                fi
            fi
            
            # Process 2560px version if needed
            if [ "$large_needs_update" = "yes" ]; then
                if process_image "$image_path" "$LARGE_OUTPUT" "$SIZE_LARGE"; then
                    update_index "$image_path" "$LARGE_OUTPUT"
                else
                    echo "      FAILED to process 2560px version"
                    ((TOTAL_ERRORS++))
                fi
            fi
            
        done
        
        if [ $batch_processed -gt 0 ] || [ $batch_updated -gt 0 ]; then
            echo "   Summary: $batch_processed new, $batch_updated updated, $batch_skipped skipped"
        elif [ $batch_skipped -gt 0 ]; then
            echo "   ✓ All images up-to-date ($batch_skipped files)"
        fi
        
        ((dir_processed += batch_processed))
        ((dir_skipped += batch_skipped))
        ((dir_updated += batch_updated))
        
    done
    
    echo ""
    echo "─────────────────────────────────────────────────────────"
    echo "$TARGET_SUBDIR totals: $dir_processed new, $dir_updated updated, $dir_skipped skipped"
    echo "─────────────────────────────────────────────────────────"
    
    ((TOTAL_PROCESSED += dir_processed))
    ((TOTAL_SKIPPED += dir_skipped))
    ((TOTAL_UPDATED += dir_updated))
}

# ============================================================================
# Main execution
# ============================================================================

START_TIME=$(date +%s)

process_source_type "$SOURCE_ROLLFILM" "rollfilm"
process_source_type "$SOURCE_SHEETFILM" "sheetfilm"

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "════════════════════════════════════════════════════════"
echo "🎉 Processing Complete!"
echo "════════════════════════════════════════════════════════"
echo "New images processed:  $TOTAL_PROCESSED"
echo "Updated images:        $TOTAL_UPDATED"
echo "Skipped (up-to-date):  $TOTAL_SKIPPED"
echo "Errors:                $TOTAL_ERRORS"
echo "Total time:            ${DURATION}s"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "1. Run: python library_scanner.py"
echo "2. Run: python update_database.py"
echo "   (This will extract EXIF and update the database)"
echo ""
