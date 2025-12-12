#!/bin/bash

echo "=== ImageArchive API Diagnostic ==="
echo ""

# Test 1: Is API server running?
echo "1. Checking if API server is running on port 5000..."
if netstat -tlnp 2>/dev/null | grep -q ":5000 "; then
    echo "   ✓ Port 5000 is listening"
else
    if ss -tlnp 2>/dev/null | grep -q ":5000 "; then
        echo "   ✓ Port 5000 is listening"
    else
        echo "   ✗ Port 5000 is NOT listening"
        echo "   → Start API server: python api_server.py"
        exit 1
    fi
fi

# Test 2: Can we reach the API?
echo ""
echo "2. Testing API endpoint /api/images..."
RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:5000/api/images 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✓ API responds with 200 OK"
    IMAGE_COUNT=$(echo "$BODY" | grep -o '"count":[0-9]*' | cut -d: -f2)
    if [ -n "$IMAGE_COUNT" ]; then
        echo "   ✓ Found $IMAGE_COUNT images in response"
    fi
else
    echo "   ✗ API returned HTTP $HTTP_CODE"
    echo "   Response: $BODY"
    exit 1
fi

# Test 3: Check through nginx if available
echo ""
echo "3. Testing through nginx proxy..."
if curl -s http://localhost/api/images > /dev/null 2>&1; then
    echo "   ✓ Nginx proxy works"
else
    echo "   ⚠ Nginx proxy not accessible (might not be configured)"
fi

# Test 4: Check CORS headers
echo ""
echo "4. Checking CORS headers..."
CORS_HEADER=$(curl -s -I http://localhost:5000/api/images | grep -i "access-control-allow-origin")
if [ -n "$CORS_HEADER" ]; then
    echo "   ✓ CORS headers present: $CORS_HEADER"
else
    echo "   ⚠ No CORS headers (might cause browser issues)"
fi

echo ""
echo "=== Diagnostic Complete ==="
echo ""
echo "If all tests passed, the API is working correctly."
echo "Check browser console (F12) for JavaScript errors."

