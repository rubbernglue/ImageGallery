"""
Authentication configuration for ImageArchive API.
Keep this file secure and out of version control!
"""

import hashlib

# Secret key for password hashing - CHANGE THIS TO A RANDOM VALUE!
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = 'change_this_to_a_random_secret_key_generated_above'

# ============================================================================
# User credentials with salted hashed passwords
# ============================================================================
# To add a new user:
# 1. Run: python generate_password_hash.py
# 2. Enter username and password when prompted
# 3. Copy the entire dictionary entry (including the username line)
# 4. Paste it into the USERS dictionary below
#
# EXAMPLE OUTPUT from generate_password_hash.py:
#     'myusername': {
#         'salt': 'a1b2c3d4e5f6...',
#         'hash': '1234567890abcdef...'
#     },
#
# The script generates both the salt AND the hash for you!
# Just copy-paste the entire block including the username.
# ============================================================================

USERS = {
    # Default admin user - password: 'admin123' - CHANGE THIS!
    'admin': {
        'salt': '8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d',
        'hash': hashlib.pbkdf2_hmac('sha256', b'admin123', b'8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d', 100000).hex()
    },
    # Add more users below by running: python generate_password_hash.py
    # Then copy-paste the output here:
    
}

# Token expiration time in seconds (24 hours)
TOKEN_EXPIRATION = 86400
