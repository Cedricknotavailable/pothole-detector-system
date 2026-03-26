"""
Test script to verify the /api/audit-log endpoint is working.
Run this while the Flask app is running.

Usage: python test_audit_endpoint.py
"""
import requests
import sys

BASE_URL = 'http://127.0.0.1:5000'

print("Testing /api/audit-log endpoint...")
print(f"Base URL: {BASE_URL}\n")

try:
    # Test the endpoint
    url = f'{BASE_URL}/api/audit-log?page=1'
    print(f"GET {url}")
    response = requests.get(url)
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✓ SUCCESS!")
        print(f"  Total entries: {data.get('total', 0)}")
        print(f"  Page: {data.get('page', 0)} of {data.get('pages', 0)}")
        print(f"  Action types: {data.get('action_types', [])}")
        print(f"  Items returned: {len(data.get('items', []))}")
        
        if data.get('items'):
            print(f"\n  Sample entries:")
            for item in data['items'][:3]:
                print(f"    - {item['timestamp_iso']} | {item['actor_username']} | {item['action']}")
        
        print("\n✓ Audit log endpoint is working correctly!")
        sys.exit(0)
    elif response.status_code == 403:
        print(f"\n✗ FORBIDDEN (403)")
        print(f"  You need to be logged in as an admin to access this endpoint.")
        print(f"  The endpoint requires admin privileges.")
        sys.exit(1)
    elif response.status_code == 404:
        print(f"\n✗ NOT FOUND (404)")
        print(f"  The endpoint doesn't exist. Check if Flask app is running.")
        sys.exit(1)
    else:
        print(f"\n✗ ERROR ({response.status_code})")
        print(f"  Response: {response.text[:500]}")
        sys.exit(1)
        
except requests.exceptions.ConnectionError:
    print("\n✗ CONNECTION ERROR")
    print(f"  Could not connect to Flask app at {BASE_URL}")
    print(f"  Make sure the Flask app is running:")
    print(f"    python app.py")
    sys.exit(1)
except Exception as e:
    print(f"\n✗ UNEXPECTED ERROR")
    print(f"  {type(e).__name__}: {e}")
    sys.exit(1)
