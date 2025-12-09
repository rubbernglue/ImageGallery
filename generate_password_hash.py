#!/usr/bin/env python3
"""
Helper script to generate secure password hashes for ImageArchive users.
Run this to create password hashes to add to api_server.py USERS dictionary.
"""

import hashlib
import secrets
import getpass

def generate_password_hash(password, salt=None):
    """Generate a secure password hash using PBKDF2."""
    if salt is None:
        salt = secrets.token_hex(16)
    
    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode(),
        salt.encode(),
        100000  # 100,000 iterations
    ).hex()
    
    return salt, password_hash

def main():
    print("=== ImageArchive Password Hash Generator ===\n")
    print("This will generate a secure hash for a user password.")
    print("Add the output to the USERS dictionary in api_server.py\n")
    
    username = input("Enter username: ").strip()
    if not username:
        print("Username cannot be empty")
        return
    
    password = getpass.getpass("Enter password: ")
    if not password:
        print("Password cannot be empty")
        return
    
    password_confirm = getpass.getpass("Confirm password: ")
    if password != password_confirm:
        print("Passwords do not match!")
        return
    
    salt, password_hash = generate_password_hash(password)
    
    print(f"\n=== Generated Password Hash ===")
    print(f"\nAdd this to api_server.py USERS dictionary:\n")
    print(f"    '{username}': {{")
    print(f"        'salt': '{salt}',")
    print(f"        'hash': '{password_hash}'")
    print(f"    }},")
    print(f"\nSalt: {salt}")
    print(f"Hash: {password_hash}")
    print(f"\nKeep this information secure!")

if __name__ == '__main__':
    main()
