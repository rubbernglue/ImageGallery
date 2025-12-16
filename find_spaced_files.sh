#!/bin/bash

# Simple script to find files/directories with spaces

TARGET_LIBRARY="/opt/media"

echo "Finding files and directories with spaces..."
echo ""

echo "=== Directories with spaces ==="
find "$TARGET_LIBRARY" -type d -name "* *" 2>/dev/null | head -20

echo ""
echo "=== Files with spaces ==="  
find "$TARGET_LIBRARY" -type f -name "* *" 2>/dev/null | head -20

echo ""
echo "=== Count ==="
DIR_COUNT=$(find "$TARGET_LIBRARY" -type d -name "* *" 2>/dev/null | wc -l)
FILE_COUNT=$(find "$TARGET_LIBRARY" -type f -name "* *" 2>/dev/null | wc -l)

echo "Directories with spaces: $DIR_COUNT"
echo "Files with spaces: $FILE_COUNT"

