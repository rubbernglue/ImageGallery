#!/bin/bash

# Script to rename files with spaces to underscored versions
# This fixes physical files to match what update_all.py expects

TARGET_LIBRARY="/opt/media"

echo "========================================"
echo "Rename Spaced Files to Underscored"
echo "========================================"
echo ""

RENAMED=0
ERRORS=0

# Find all files with spaces in rollfilm and sheetfilm
find "$TARGET_LIBRARY/rollfilm" "$TARGET_LIBRARY/sheetfilm" -type f -name "* *" 2>/dev/null | while IFS= read -r file; do
    
    # Get directory and filename
    dir=$(dirname "$file")
    filename=$(basename "$file")
    
    # Skip if file doesn't exist (race condition)
    if [ ! -f "$file" ]; then
        continue
    fi
    
    # Create new filename with underscores
    new_filename="${filename// /_}"
    new_path="$dir/$new_filename"
    
    # Skip if target already exists
    if [ -f "$new_path" ]; then
        echo "  ⚠ Target exists, skipping: $filename"
        continue
    fi
    
    # Rename the file
    mv "$file" "$new_path"
    
    if [ $? -eq 0 ]; then
        echo "  ✓ $filename"
        echo "    → $new_filename"
        ((RENAMED++))
    else
        echo "  ✗ Failed: $filename"
        ((ERRORS++))
    fi
done

# Also rename directories with spaces
find "$TARGET_LIBRARY/rollfilm" "$TARGET_LIBRARY/sheetfilm" -mindepth 2 -maxdepth 2 -type d -name "* *" 2>/dev/null | while IFS= read -r dir; do
    
    parent=$(dirname "$dir")
    dirname_old=$(basename "$dir")
    dirname_new="${dirname_old// /_}"
    new_dir_path="$parent/$dirname_new"
    
    # Skip if target already exists
    if [ -d "$new_dir_path" ]; then
        echo "  ⚠ Dir exists, skipping: $dirname_old"
        continue
    fi
    
    # Rename directory
    mv "$dir" "$new_dir_path"
    
    if [ $? -eq 0 ]; then
        echo "  ✓ Dir: $dirname_old → $dirname_new"
        ((RENAMED++))
    else
        echo "  ✗ Failed dir: $dirname_old"
        ((ERRORS++))
    fi
done

echo ""
echo "========================================"
echo "✓ Rename Complete!"
echo "========================================"
echo "Renamed: $RENAMED"
echo "Errors: $ERRORS"
echo ""

if [ $RENAMED -gt 0 ]; then
    echo "Now run:"
    echo "  python fix_spaced_filenames.py"
    echo ""
    echo "This will update the database to point to the renamed files."
fi

