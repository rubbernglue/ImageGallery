#!/bin/bash

# Script to remove old directories with # characters
# These are generated files, not originals - safe to delete

TARGET_LIBRARY="/mnt/omv/Photo/Picture_library"

echo "========================================"
echo "Remove Old # Directories"
echo "========================================"
echo ""

# Find all directories with # in rollfilm and sheetfilm
OLD_DIRS=$(find "$TARGET_LIBRARY/rollfilm" "$TARGET_LIBRARY/sheetfilm" -maxdepth 1 -type d -name "*#*" 2>/dev/null)

if [ -z "$OLD_DIRS" ]; then
    echo "✓ No directories with # characters found"
    echo "  Filesystem is already clean!"
    exit 0
fi

echo "Found directories with # characters:"
echo ""

COUNT=0
while IFS= read -r dir; do
    if [ -n "$dir" ]; then
        ((COUNT++))
        DIR_NAME=$(basename "$dir")
        NEW_NAME="${DIR_NAME//#/n}"
        NEW_PATH="$(dirname "$dir")/$NEW_NAME"
        
        echo "$COUNT. $DIR_NAME"
        if [ -d "$NEW_PATH" ]; then
            echo "   ✓ Replacement exists: $NEW_NAME"
        else
            echo "   ⚠ No replacement (will still delete - these are generated)"
        fi
    fi
done <<< "$OLD_DIRS"

echo ""
echo "These are generated directories (not originals)."
echo "They will be safely removed."
echo ""
read -p "Delete $COUNT directories? [yes/NO]: " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "Removing directories..."
echo ""

REMOVED=0
ERRORS=0

while IFS= read -r dir; do
    if [ -n "$dir" ]; then
        DIR_NAME=$(basename "$dir")
        rm -rf "$dir"
        if [ $? -eq 0 ]; then
            echo "  ✓ Removed: $DIR_NAME"
            ((REMOVED++))
        else
            echo "  ✗ Failed: $DIR_NAME"
            ((ERRORS++))
        fi
    fi
done <<< "$OLD_DIRS"

echo ""
echo "========================================"
echo "✓ Cleanup Complete!"
echo "========================================"
echo "Removed: $REMOVED"
echo "Errors: $ERRORS"
echo ""

if [ $REMOVED -gt 0 ]; then
    echo "Old directories removed successfully!"
    echo "Your archive is now clean."
fi

