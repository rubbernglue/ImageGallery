# Debugging Connection Issues

## If the frontend won't connect to the backend

### Step 1: Check the Browser Console

1. Open the website
2. Press F12 to open Developer Tools
3. Click the "Console" tab
4. Look for errors in red

**What to look for:**

```
[API] Fetching images from: /api/images
[API] Response status: 200
[API] Successfully loaded 8988 image records
```

If you see this ✓ - connection is working!

**Common errors:**

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Failed to fetch` | API server not running | Run `python api_server.py` |
| `Status: 404` | Nginx not configured | Check nginx config |
| `Status: 502` | API server down but nginx up | Start API server |
| `CORS error` | CORS not configured | Check api_server.py CORS settings |
| `Invalid API response format` | API returned wrong data | Check API server logs |

### Step 2: Test the API Directly

Open the minimal test page I created:
```bash
# Open test_frontend.html in your browser
# Should show: ✓ Connection successful! with image count
```

Or test with curl:
```bash
curl -v http://localhost:5000/api/images
# Should return JSON with images array
```

### Step 3: Check API Server is Running

```bash
# Check if process is running
ps aux | grep api_server.py

# Check if port 5000 is listening
netstat -tlnp | grep 5000
# or
ss -tlnp | grep 5000

# Check API server logs
# (look at terminal where you ran python api_server.py)
```

### Step 4: Check Nginx Configuration

```bash
# Test nginx config
sudo nginx -t

# Check nginx is running
sudo systemctl status nginx

# Check nginx error logs
sudo tail -f /var/log/nginx/api_error.log
```

### Step 5: Compare with Old Version

If old version works but new doesn't, check:

1. **API_BASE_URL difference:**
   ```bash
   # Old version might have had:
   const API_BASE_URL = 'http://localhost:5000/api/images';
   
   # New version has:
   const API_BASE_URL = '/api/images';
   ```

2. **Test both URLs in browser console:**
   ```javascript
   // Test absolute URL
   fetch('http://172.16.8.26:5000/api/images').then(r => r.json()).then(console.log)
   
   // Test relative URL
   fetch('/api/images').then(r => r.json()).then(console.log)
   ```

## Quick Fixes

### Fix 1: Use Absolute URL (Bypass Nginx)

If you need to quickly test, edit `image_gallery.html`:

```javascript
// Line ~294, change from:
const API_BASE_URL = '/api/images';

// To:
const API_BASE_URL = 'http://172.16.8.26:5000/api/images';
```

**Note:** This bypasses nginx and may cause mixed content errors on HTTPS.

### Fix 2: Disable Authentication Temporarily

If auth is causing issues, comment out the auth check in init():

```javascript
// Line ~1100, comment out:
// checkStoredAuth();
```

This skips authentication on page load (you can still login manually).

### Fix 3: Check JavaScript Console for Errors

Look for:
- `ReferenceError` - undefined variable
- `TypeError` - wrong type
- `SyntaxError` - code syntax error

Most common: Missing closing bracket or quote.

## Testing Checklist

- [ ] API server running (`python api_server.py`)
- [ ] Can access http://172.16.8.26:5000/api/images directly
- [ ] Nginx running and configured
- [ ] Browser console shows no errors
- [ ] test_frontend.html works
- [ ] No JavaScript syntax errors

## Common Solutions

### "Connection refused"
```bash
# API server not running
python api_server.py
```

### "404 Not Found"
```bash
# Nginx not proxying correctly
# Check nginx_imagearchive.conf location /api/ block
sudo nginx -t
sudo nginx -s reload
```

### "CORS error"
```bash
# Check api_server.py has CORS configured
# Should have near line 30:
# CORS(app, resources={r"/api/*": {...}})
```

### JavaScript doesn't run at all
- Check browser console for syntax errors
- The syntax error on line 769 is now fixed
- Reload with Ctrl+Shift+R (hard reload)

### Page loads but gallery is empty
- Check browser console: `[API] Successfully loaded X records`
- If 0 records, database is empty
- Run: `python setup_database.py`

