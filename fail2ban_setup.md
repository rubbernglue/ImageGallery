# Fail2Ban Setup for ImageArchive

## Overview

Protect your ImageArchive from brute-force login attempts using fail2ban. Failed login attempts are logged and IP addresses are automatically blocked after too many failures.

## Installation

### Step 1: Install fail2ban

```bash
sudo apt-get update
sudo apt-get install fail2ban
```

### Step 2: Create Log Directory

```bash
sudo mkdir -p /var/log/imagearchive
sudo chown www-data:www-data /var/log/imagearchive
sudo chmod 755 /var/log/imagearchive
```

### Step 3: Install Filter Configuration

```bash
sudo cp fail2ban_imagearchive.conf /etc/fail2ban/filter.d/imagearchive.conf
sudo chmod 644 /etc/fail2ban/filter.d/imagearchive.conf
```

### Step 4: Install Jail Configuration

```bash
sudo cp fail2ban_imagearchive.jail /etc/fail2ban/jail.d/imagearchive.local
sudo chmod 644 /etc/fail2ban/jail.d/imagearchive.local
```

### Step 5: Restart fail2ban

```bash
sudo systemctl restart fail2ban
sudo systemctl status fail2ban
```

### Step 6: Verify Configuration

```bash
# Check that the jail is active
sudo fail2ban-client status imagearchive

# Should show:
# Status for the jail: imagearchive
# |- Filter
# |  |- Currently failed: 0
# |  |- Total failed:     0
# |  `- File list:        /var/log/imagearchive/auth.log
# `- Actions
#    |- Currently banned: 0
#    |- Total banned:     0
#    `- Banned IP list:
```

## How It Works

### Log Format

The API server writes to `/var/log/imagearchive/auth.log` in this format:

**Successful login:**
```
2025-12-11 22:30:15 SUCCESS: user=admin ip=192.168.1.100
```

**Failed login:**
```
2025-12-11 22:30:20 FAILED: user=admin ip=192.168.1.100
```

### fail2ban Detection

The filter looks for lines with `FAILED:` and extracts the IP address.

**After 5 failed attempts within 10 minutes:**
1. IP is banned for 1 hour
2. All requests from that IP are blocked
3. Ban is logged to fail2ban log

### Configuration Options

Edit `/etc/fail2ban/jail.d/imagearchive.local` to adjust:

```ini
maxretry = 5      # Number of failures before ban
findtime = 600    # Time window (10 minutes)
bantime = 3600    # Ban duration (1 hour)
```

**Recommended settings:**

| Security Level | maxretry | findtime | bantime |
|----------------|----------|----------|---------|
| Strict | 3 | 300 (5 min) | 7200 (2 hrs) |
| Normal | 5 | 600 (10 min) | 3600 (1 hr) |
| Lenient | 10 | 900 (15 min) | 1800 (30 min) |

## Testing

### Test the Filter

```bash
# Add a test entry to the log
sudo bash -c 'echo "2025-12-11 22:30:20 FAILED: user=testuser ip=1.2.3.4" >> /var/log/imagearchive/auth.log'

# Test the filter
sudo fail2ban-regex /var/log/imagearchive/auth.log /etc/fail2ban/filter.d/imagearchive.conf

# Should show:
# Success, the total number of match is 1
```

### Test Real Login Failures

1. Try logging in with wrong password 5 times
2. Check fail2ban status:
   ```bash
   sudo fail2ban-client status imagearchive
   ```
3. You should see your IP in "Banned IP list"

### Unban an IP

```bash
# Unban specific IP
sudo fail2ban-client set imagearchive unbanip 192.168.1.100

# Unban all IPs
sudo fail2ban-client unban --all
```

## Monitoring

### View Banned IPs

```bash
sudo fail2ban-client status imagearchive
```

### View Recent Failed Attempts

```bash
tail -f /var/log/imagearchive/auth.log
```

### View fail2ban Log

```bash
sudo tail -f /var/log/fail2ban.log
```

## Integration with Nginx

If you're using nginx as reverse proxy (recommended), make sure it forwards the real IP:

In `nginx_imagearchive.conf`:
```nginx
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

The API server reads `X-Real-IP` header to get the actual client IP.

## Log Rotation

Create `/etc/logrotate.d/imagearchive`:

```
/var/log/imagearchive/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 www-data www-data
    sharedscripts
    postrotate
        systemctl reload fail2ban > /dev/null 2>&1 || true
    endscript
}
```

Apply:
```bash
sudo logrotate -f /etc/logrotate.d/imagearchive
```

## Troubleshooting

### fail2ban not starting

```bash
# Check configuration
sudo fail2ban-client -t

# Check logs
sudo journalctl -u fail2ban -n 50
```

### Jail not active

```bash
# Check if file exists
ls -la /etc/fail2ban/jail.d/imagearchive.local

# Check if filter exists
ls -la /etc/fail2ban/filter.d/imagearchive.conf

# Reload fail2ban
sudo fail2ban-client reload
```

### Not detecting failed logins

```bash
# Check log file exists and is writable
ls -la /var/log/imagearchive/auth.log

# Check log format matches filter
tail /var/log/imagearchive/auth.log

# Test filter manually
sudo fail2ban-regex /var/log/imagearchive/auth.log /etc/fail2ban/filter.d/imagearchive.conf
```

### Accidentally banned yourself

```bash
# Unban your IP
sudo fail2ban-client set imagearchive unbanip YOUR_IP_ADDRESS

# Or stop fail2ban temporarily
sudo systemctl stop fail2ban
```

## Summary

After setup, fail2ban will:
- ✅ Monitor `/var/log/imagearchive/auth.log`
- ✅ Detect failed login attempts
- ✅ Ban IPs after 5 failures in 10 minutes
- ✅ Automatically unban after 1 hour
- ✅ Log all actions to `/var/log/fail2ban.log`

Your ImageArchive is now protected against brute-force attacks!

