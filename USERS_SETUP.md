# Setting Up Users - Step by Step Guide

## Quick Start

### Step 1: Generate a Password Hash

Run the password generator:
```bash
python generate_password_hash.py
```

You'll see:
```
=== ImageArchive Password Hash Generator ===

This will generate a secure hash for a user password.
Add the output to the USERS dictionary in api_server.py

Enter username: myuser
Enter password: [your password - won't show on screen]
Confirm password: [your password again]

=== Generated Password Hash ===

Add this to api_server.py USERS dictionary:

    'myuser': {
        'salt': '6f59093c2de155b6c91838e2b3afe76f',
        'hash': '946fa98b36a048dc4e9d6625fe6ba474d84bfc44b75573d2f8c0e9b06838584f'
    },

Salt: 6f59093c2de155b6c91838e2b3afe76f
Hash: 946fa98b36a048dc4e9d6625fe6ba474d84bfc44b75573d2f8c0e9b06838584f
```

### Step 2: Copy the Entire Block

**Copy everything from the script output**, including:
- The username line: `'myuser': {`
- The salt line: `'salt': '...',`
- The hash line: `'hash': '...'`
- The closing brace: `},`

### Step 3: Paste Into api_server.py

Open `api_server.py` and find the USERS dictionary. It looks like this:

```python
USERS = {
    # Default admin user - password: 'admin123' - CHANGE THIS!
    'admin': {
        'salt': '8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d',
        'hash': hashlib.pbkdf2_hmac('sha256', b'admin123', b'8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d', 100000).hex()
    },
    # Add more users below:
    
}
```

**Paste your copied text** after the comment line:

```python
USERS = {
    # Default admin user - password: 'admin123' - CHANGE THIS!
    'admin': {
        'salt': '8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d',
        'hash': hashlib.pbkdf2_hmac('sha256', b'admin123', b'8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d', 100000).hex()
    },
    # Add more users below:
    'myuser': {
        'salt': '6f59093c2de155b6c91838e2b3afe76f',
        'hash': '946fa98b36a048dc4e9d6625fe6ba474d84bfc44b75573d2f8c0e9b06838584f'
    },
}
```

### Step 4: Restart the API Server

```bash
# Stop the current server (Ctrl+C)
python api_server.py
```

### Step 5: Test Login

Open the website and log in with:
- Username: `myuser`
- Password: `[the password you entered in step 1]`

## Complete Example

Let's say you want to create a user "photographer" with password "MySecure123!":

### 1. Generate Hash:
```bash
$ python generate_password_hash.py
Enter username: photographer
Enter password: [type: MySecure123!]
Confirm password: [type: MySecure123!]

=== Generated Password Hash ===

    'photographer': {
        'salt': 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6',
        'hash': 'f8e9d8c7b6a5948372615049382716059483726150493827160594837261504938'
    },
```

### 2. Your USERS dictionary becomes:
```python
USERS = {
    'admin': {
        'salt': '8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d',
        'hash': hashlib.pbkdf2_hmac('sha256', b'admin123', b'8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d', 100000).hex()
    },
    'photographer': {
        'salt': 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6',
        'hash': 'f8e9d8c7b6a5948372615049382716059483726150493827160594837261504938'
    },
}
```

### 3. Login with:
- Username: `photographer`
- Password: `MySecure123!`

## Adding Multiple Users

You can have as many users as you want. Just run the script multiple times and add each one:

```python
USERS = {
    'admin': {
        'salt': '...',
        'hash': '...'
    },
    'photographer1': {
        'salt': '...',
        'hash': '...'
    },
    'photographer2': {
        'salt': '...',
        'hash': '...'
    },
    'editor': {
        'salt': '...',
        'hash': '...'
    },
}
```

## Removing the Default Admin

Once you've created your own user and tested it works:

1. Create your user account (follow steps above)
2. Test logging in with your new account
3. Once confirmed working, remove or replace the 'admin' entry:

```python
USERS = {
    'myuser': {
        'salt': '6f59093c2de155b6c91838e2b3afe76f',
        'hash': '946fa98b36a048dc4e9d6625fe6ba474d84bfc44b75573d2f8c0e9b06838584f'
    },
    # admin removed - you can delete the admin entry
}
```

## Understanding the Format

**YOU DO NOT need to understand this to use the system**, but for reference:

- **salt**: A random string that makes each password unique (even if two users have the same password)
- **hash**: The encrypted version of the password (cannot be reversed to get the original password)
- Both are generated automatically by `generate_password_hash.py`

The script does ALL the work - you just copy and paste!

## Troubleshooting

### "Invalid credentials" error

**Check:**
1. Did you paste the ENTIRE block including the username line?
2. Did you restart the API server after changing the file?
3. Are you typing the username exactly as it appears (case-sensitive)?
4. Are you using the same password you entered when running the generator?

### "Module not found" error when starting server

Make sure you have Python packages installed:
```bash
pip install flask flask-cors psycopg2-binary
```

### Still not working?

Try creating a simple test user:

```bash
# Generate with password "test123"
python generate_password_hash.py
# Enter: testuser / test123 / test123

# Add to USERS dictionary
# Restart server
# Try logging in with testuser / test123
```

If that works, the problem was with how you were copying/pasting or typing your actual username/password.
