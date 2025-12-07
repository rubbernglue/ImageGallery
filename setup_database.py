#!/usr/bin/env python3
"""
Database setup script for ImageArchive.
This script will:
1. Create the database if it doesn't exist
2. Create all tables from database_schema.sql
3. Optionally populate the database from image_data.json
"""

import os
import sys
import json
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Database configuration - update these to match your PostgreSQL setup
DB_CONFIG = {
    'database': 'imagearchive',
    'user': 'postgres',
    'password': 'xxxxx',
    'host': 'localhost',
    'port': '5432'
}

def create_database():
    """Creates the imagearchive database if it doesn't exist."""
    try:
        # Connect to PostgreSQL server (to 'postgres' database)
        conn = psycopg2.connect(
            database='postgres',
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port']
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        with conn.cursor() as cur:
            # Check if database exists
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (DB_CONFIG['database'],))
            exists = cur.fetchone()
            
            if not exists:
                print(f"Creating database '{DB_CONFIG['database']}'...")
                cur.execute(f"CREATE DATABASE {DB_CONFIG['database']};")
                print(f"Database '{DB_CONFIG['database']}' created successfully.")
            else:
                print(f"Database '{DB_CONFIG['database']}' already exists.")
        
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating database: {e}")
        return False

def create_tables():
    """Creates all tables from the database_schema.sql file."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        # Read schema file
        schema_file = 'database_schema.sql'
        if not os.path.exists(schema_file):
            print(f"Error: {schema_file} not found.")
            return False
        
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        print("Creating tables from schema...")
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        
        conn.commit()
        conn.close()
        print("Tables created successfully.")
        return True
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

def populate_from_json():
    """Populates the database from image_data.json if it exists."""
    json_file = 'image_data.json'
    
    if not os.path.exists(json_file):
        print(f"\n{json_file} not found. Skipping data population.")
        print("Run 'python library_scanner.py' to generate image_data.json first.")
        return True
    
    try:
        with open(json_file, 'r') as f:
            images = json.load(f)
        
        if not images:
            print("No images found in image_data.json")
            return True
        
        conn = psycopg2.connect(**DB_CONFIG)
        
        print(f"\nPopulating database with {len(images)} images...")
        inserted = 0
        skipped = 0
        
        with conn:
            with conn.cursor() as cur:
                for image in images:
                    try:
                        # Insert image (skip if already exists)
                        insert_sql = """
                            INSERT INTO images 
                            (image_id, film_type, batch_info, filename_base, film_stock, 
                             thumbnail_path, highres_path, description)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (image_id) DO NOTHING;
                        """
                        cur.execute(insert_sql, (
                            image['image_id'],
                            image['film_type'],
                            image['batch_info'],
                            image['filename_base'],
                            image['film_stock'],
                            image['thumbnail_path'],
                            image['highres_path'],
                            image.get('description', '')
                        ))
                        
                        if cur.rowcount > 0:
                            inserted += 1
                        else:
                            skipped += 1
                            
                    except Exception as e:
                        print(f"Error inserting image {image.get('image_id', 'unknown')}: {e}")
        
        conn.close()
        print(f"Data population complete: {inserted} images inserted, {skipped} skipped (already exist).")
        return True
    except Exception as e:
        print(f"Error populating data: {e}")
        return False

def verify_setup():
    """Verifies the database setup by counting records."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM images;")
            image_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM tags;")
            tag_count = cur.fetchone()[0]
        
        conn.close()
        
        print(f"\n=== Database Setup Verification ===")
        print(f"Total images: {image_count}")
        print(f"Total tags: {tag_count}")
        print(f"Database is ready to use!")
        return True
    except Exception as e:
        print(f"Error verifying setup: {e}")
        return False

def main():
    print("=== ImageArchive Database Setup ===\n")
    
    # Step 1: Create database
    if not create_database():
        sys.exit(1)
    
    # Step 2: Create tables
    if not create_tables():
        sys.exit(1)
    
    # Step 3: Populate with data
    if not populate_from_json():
        sys.exit(1)
    
    # Step 4: Verify
    if not verify_setup():
        sys.exit(1)
    
    print("\n=== Setup Complete ===")
    print("You can now run the API server with: python api_server.py")
    print("Don't forget to update DB_CONFIG in both setup_database.py and api_server.py if needed.")

if __name__ == '__main__':
    main()
