# Fixing Token Issues with Gunicorn Workers

## The Problem

You're running Gunicorn with 3 workers:
```bash
gunicorn --workers 3 ...
```

**What happens:**
1. Login request → Goes to Worker 1 → Token saved in Worker 1's memory
2. Tag request → Goes to Worker 2 → Token not found (different worker!)
3. Result: "Invalid or expired token"

**Why:**
- Each worker has its own memory space
- Tokens saved to `/tmp/imagearchive_tokens.json` 
- But only loaded on startup
- Workers don't share in-memory tokens

## Solutions

### Option 1: Use Single Worker (Simplest)

**Edit your Gunicorn command:**
```bash
# Before:
gunicorn --workers 3 --bind 0.0.0.0:5000 api_server:app ...

# After:
gunicorn --workers 1 --bind 0.0.0.0:5000 api_server:app ...
```

**Pros:**
- ✅ Immediate fix
- ✅ No code changes
- ✅ Tokens work perfectly

**Cons:**
- ⚠️ Less concurrent request handling
- ⚠️ But for your use case (few users), single worker is fine!

### Option 2: Reload Tokens from Disk on Each Request

**Edit api_server.py** - Change token validation to reload from disk:

```python
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Reload tokens from disk on each request
        load_persisted_tokens()  # Add this line
        
        auth_header = request.headers.get('Authorization')
        # ... rest of function
```

**Pros:**
- ✅ Works with multiple workers
- ✅ Tokens shared via file

**Cons:**
- ⚠️ Slower (disk read on every request)
- ⚠️ File I/O overhead

### Option 3: Use Redis for Token Storage (Production)

Store tokens in Redis instead of in-memory:

```python
import redis
r = redis.Redis(host='localhost', port=6379)

# Store token
r.setex(token, TOKEN_EXPIRATION, json.dumps(token_data))

# Get token
token_data = json.loads(r.get(token))
```

**Pros:**
- ✅ Works with any number of workers
- ✅ Fast
- ✅ Production-ready

**Cons:**
- ⚠️ Requires Redis installation
- ⚠️ More setup complexity

### Option 4: Use Database for Token Storage

Store tokens in PostgreSQL:

```sql
CREATE TABLE auth_tokens (
    token VARCHAR(64) PRIMARY KEY,
    username VARCHAR(100),
    expires TIMESTAMP
);
```

**Pros:**
- ✅ Works with multiple workers
- ✅ No extra dependencies

**Cons:**
- ⚠️ Database overhead on every request
- ⚠️ Needs migration

## Recommended Solution: Single Worker

For your use case (small number of concurrent users), **use 1 worker**:

```bash
gunicorn --workers 1 --bind 0.0.0.0:5000 api_server:app \
  --access-logfile /var/log/apibackend/access.log \
  --error-logfile /var/log/apibackend/error.log
```

**Why this is fine:**
- You have few concurrent users
- Single worker handles 500+ requests/sec
- Authentication works perfectly
- Simple and reliable

### How to Apply

**1. Stop Gunicorn:**
```bash
sudo systemctl stop apibackend
# or
pkill gunicorn
```

**2. Edit systemd service file:**
```bash
sudo nano /etc/systemd/system/apibackend.service

# Find the ExecStart line and change --workers 3 to --workers 1
```

**3. Reload and restart:**
```bash
sudo systemctl daemon-reload
sudo systemctl start apibackend
sudo systemctl status apibackend
```

**4. Test:**
- Log in
- Add a tag
- Add another tag
- Both should work! ✓

## Verification

**After changing to 1 worker, check:**

```bash
ps aux | grep gunicorn

# Should show:
gunicorn: master [api_server:app]
gunicorn: worker [api_server:app]  ← Only ONE worker
```

**Then test authentication:**
- Login works
- Tokens persist
- No more "Invalid or expired token" errors

## If You Need Multiple Workers

If you really need 3+ workers for performance, implement **Option 2** (reload from disk) or **Option 3** (Redis).

For now, **single worker is the quickest fix** and works perfectly for your needs!

