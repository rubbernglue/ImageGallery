# Troubleshooting Bulk Tagging Failures

## Common Causes of Failures

### 1. Rate Limiting (nginx)

**Symptom:** Some images fail randomly, especially when tagging many at once

**Cause:** nginx `limit_req` blocking too many requests

**Check nginx config:**
```nginx
limit_req zone=api_limit burst=10 nodelay;
```

**Solution:** Increase burst limit in `nginx_imagearchive.conf`:
```nginx
limit_req zone=api_limit burst=50 nodelay;  # Increased from 10
```

Then reload nginx:
```bash
sudo nginx -s reload
```

### 2. Database Connection Timeout

**Symptom:** Later images in batch fail

**Cause:** Database connection pool exhausted

**Check API server logs:**
```bash
# Look for:
Database connection error: too many connections
```

**Solution:** Increase PostgreSQL max_connections or add connection pooling

### 3. Special Characters in image_id

**Symptom:** Specific images always fail

**Cause:** URL encoding issues with special characters

**Check console for:**
```
[BULK] Failed: rollfilm/batch/image_#001
Status: 404
```

**Solution:** Already handled by sanitization, but verify paths don't have unencoded characters

### 4. Transaction Conflicts

**Symptom:** Random failures, "could not serialize" errors

**Cause:** Multiple requests updating same image

**Rare** - should not happen with sequential processing

## Debugging Steps

### Step 1: Check Browser Console

Open console (F12) after bulk tagging fails:

```
[BULK] Failed images details:
  - rollfilm/batch/image_001
    Status: 429, Error: Too Many Requests
  - rollfilm/batch/image_002
    Status: 500, Error: Internal Server Error
```

**Status codes:**
- `429` = Rate limiting (nginx or API)
- `500` = Server error (check API logs)
- `404` = Image not found (path issue)
- `401` = Auth expired (shouldn't happen with new code)

### Step 2: Check API Server Logs

Watch API server output while bulk tagging:

```bash
python api_server.py

# Should see:
[AUTH] Token valid for user 'johan'
[DEBUG] update_tags called with image_id: ...
[SUCCESS] Tags updated for image_id=...
```

**Look for errors:**
```
Database connection error
Too many connections
Transaction aborted
```

### Step 3: Check nginx Logs

```bash
sudo tail -f /var/log/nginx/api_error.log

# Look for:
limiting requests, excess: X.XXX
upstream timed out
```

### Step 4: Test with Small Batch

Instead of 50 images, try 5:
- Select 5 images
- Add tags
- All succeed? → Rate limiting issue
- Still fail? → Other issue

## Quick Fixes

### Fix 1: Increase nginx Burst Limit

Edit `/etc/nginx/sites-available/nginx_imagearchive.conf`:

```nginx
# Find this line:
limit_req zone=api_limit burst=10 nodelay;

# Change to:
limit_req zone=api_limit burst=100 nodelay;
```

Reload nginx:
```bash
sudo nginx -t
sudo nginx -s reload
```

### Fix 2: Increase Delay Between Requests

Edit `image_gallery.html` line ~1580:

```javascript
// Find:
await new Promise(resolve => setTimeout(resolve, 100));

// Change to:
await new Promise(resolve => setTimeout(resolve, 200));  // Slower but more reliable
```

### Fix 3: Disable Rate Limiting Temporarily

In nginx config, comment out limit:

```nginx
# limit_req zone=api_limit burst=10 nodelay;
```

Test bulk tagging - if it works, the issue is rate limiting.

## Understanding the Errors

### "Tagged 36 images, 2 failed"

**Most likely causes (in order):**

1. **nginx rate limiting (80%)** - Burst limit exceeded
2. **Network timeout (10%)** - Slow connection
3. **Database issue (5%)** - Connection/transaction error
4. **Path encoding (5%)** - Special characters in image_id

### How to Identify

**Check console output:**

**Rate limiting:**
```
Status: 429, Error: Too Many Requests
```

**Timeout:**
```
Error: Failed to fetch
or
Status: 504, Error: Gateway Timeout
```

**Database:**
```
Status: 500, Error: Internal server error
```

**Path issue:**
```
Status: 404, Error: Image not found
```

## Recommended Settings

For bulk tagging to work reliably with 50+ images:

**nginx config:**
```nginx
limit_req zone=api_limit burst=100 nodelay;
```

**Frontend delay:**
```javascript
await new Promise(resolve => setTimeout(resolve, 150));
```

**PostgreSQL:**
```
max_connections = 100  (in postgresql.conf)
```

## Next Steps

1. **Check browser console** for exact error
2. **Share the error details** from console
3. **Apply the appropriate fix** based on error code

Most likely it's nginx rate limiting - increase the burst value!

