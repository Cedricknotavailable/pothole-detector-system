"""
Test script to verify the /api/reports/<report_id>/flag endpoint is working.
Run this while the Flask app is running.

Usage: python test_flag_report.py
"""
import requests
import sys

BASE_URL = 'http://127.0.0.1:8000'

def login(username, password):
    """Login and return session cookies"""
    session = requests.Session()
    response = session.post(f'{BASE_URL}/login', data={
        'username': username,
        'password': password
    })
    if response.status_code == 200 and 'user_id' in session.cookies.get_dict():
        return session
    return None

def test_flag_report():
    print("Testing /api/reports/<report_id>/flag endpoint...")
    print(f"Base URL: {BASE_URL}\n")
    
    # Test 1: Attempt to flag without authentication
    print("Test 1: Flag without authentication")
    url = f'{BASE_URL}/api/reports/1/flag'
    response = requests.post(url)
    print(f"  Status: {response.status_code}")
    if response.status_code in [302, 401, 403]:
        print("  ✓ Correctly requires authentication\n")
    else:
        print(f"  ✗ Expected 302/401/403, got {response.status_code}\n")
    
    # Test 2: Login and flag a report
    print("Test 2: Flag report as authenticated user")
    print("  Attempting login...")
    
    # Try to login with a test user (you may need to adjust credentials)
    session = login('testuser', 'testpass')
    if not session:
        session = login('admin', 'admin')
    
    if not session:
        print("  ✗ Could not login. Please create a test user or adjust credentials.")
        print("  Skipping authenticated tests.\n")
        return
    
    print("  ✓ Login successful")
    
    # Try to flag report ID 1
    report_id = 1
    url = f'{BASE_URL}/api/reports/{report_id}/flag'
    print(f"  POST {url}")
    response = session.post(url)
    
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"  ✓ SUCCESS!")
        print(f"    Flag count: {data.get('flag_count')}")
        print(f"    Auto-flagged: {data.get('auto_flagged')}")
        print(f"    Threshold: {data.get('threshold')}")
        
        # Test 3: Try to flag the same report again (should fail)
        print("\nTest 3: Attempt duplicate flag")
        response2 = session.post(url)
        print(f"  Status: {response2.status_code}")
        if response2.status_code == 400:
            data2 = response2.json()
            print(f"  ✓ Correctly prevents duplicate flags")
            print(f"    Error: {data2.get('error')}")
        else:
            print(f"  ✗ Expected 400, got {response2.status_code}")
            
    elif response.status_code == 400:
        data = response.json()
        print(f"  Response: {data}")
        if data.get('error') == 'Already flagged':
            print(f"  ✓ Report already flagged by this user")
        else:
            print(f"  ✗ Unexpected error: {data.get('error')}")
    elif response.status_code == 404:
        print(f"  ✗ Report not found (ID {report_id} doesn't exist)")
        print(f"  Try creating a report first or adjust report_id in the test")
    else:
        print(f"  ✗ Unexpected status code")
        print(f"  Response: {response.text[:500]}")

if __name__ == '__main__':
    try:
        test_flag_report()
        print("\n✓ Flag report endpoint tests completed!")
        sys.exit(0)
    except requests.exceptions.ConnectionError:
        print("\n✗ CONNECTION ERROR")
        print(f"  Could not connect to Flask app at {BASE_URL}")
        print(f"  Make sure the Flask app is running:")
        print(f"    python app.py")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
