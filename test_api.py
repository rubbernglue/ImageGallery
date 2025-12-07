#!/usr/bin/env python3
"""
Quick test script for the ImageArchive API.
Make sure the API server is running before running this script.
"""

import requests
import json

API_BASE = "http://localhost:5000/api/images"

def test_list_images():
    """Test GET /api/images"""
    print("\n=== Testing GET /api/images ===")
    response = requests.get(API_BASE)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data.get('success')}")
        print(f"Image count: {data.get('count')}")
        if data.get('images'):
            print(f"First image: {data['images'][0].get('image_id')}")
            return data['images'][0].get('image_id')  # Return first image ID for further tests
    else:
        print(f"Error: {response.text}")
    return None

def test_get_image(image_id):
    """Test GET /api/images/<image_id>"""
    print(f"\n=== Testing GET /api/images/{image_id} ===")
    response = requests.get(f"{API_BASE}/{image_id}")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data.get('success')}")
        print(f"Description: {data['image'].get('description')}")
        print(f"Tags: {data['image'].get('tags')}")
    else:
        print(f"Error: {response.text}")

def test_update_description(image_id):
    """Test PUT /api/images/<image_id>/description"""
    print(f"\n=== Testing PUT /api/images/{image_id}/description ===")
    
    new_description = "Test description updated via API"
    response = requests.put(
        f"{API_BASE}/{image_id}/description",
        headers={"Content-Type": "application/json"},
        json={"description": new_description}
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data.get('success')}")
        print(f"Message: {data.get('message')}")
    else:
        print(f"Error: {response.text}")

def test_update_tags(image_id):
    """Test POST /api/images/<image_id>/tags"""
    print(f"\n=== Testing POST /api/images/{image_id}/tags ===")
    
    new_tags = ["test", "api", "python"]
    response = requests.post(
        f"{API_BASE}/{image_id}/tags",
        headers={"Content-Type": "application/json"},
        json={"tags": new_tags}
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data.get('success')}")
        print(f"Message: {data.get('message')}")
    else:
        print(f"Error: {response.text}")

def main():
    print("=== ImageArchive API Test Suite ===")
    print("Make sure the API server is running on http://localhost:5000")
    
    try:
        # Test 1: List all images
        first_image_id = test_list_images()
        
        if not first_image_id:
            print("\n[ERROR] No images found. Run 'python setup_database.py' first.")
            return
        
        # Test 2: Get single image
        test_get_image(first_image_id)
        
        # Test 3: Update description
        test_update_description(first_image_id)
        
        # Test 4: Update tags
        test_update_tags(first_image_id)
        
        # Test 5: Verify changes
        test_get_image(first_image_id)
        
        print("\n=== All Tests Completed ===")
        
    except requests.exceptions.ConnectionError:
        print("\n[ERROR] Could not connect to API server.")
        print("Make sure the server is running: python api_server.py")
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")

if __name__ == '__main__':
    main()
