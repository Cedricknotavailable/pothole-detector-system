"""
Simple test for Activity Logs page.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app

def test_route_exists():
    """Test that the activity logs route exists"""
    with app.test_client() as client:
        # Test without login (should redirect or show error)
        response = client.get('/activity-logs')
        print(f"Response status: {response.status_code}")
        
        # Test analytics page (should work for comparison)
        response = client.get('/analytics')
        print(f"Analytics response status: {response.status_code}")

if __name__ == '__main__':
    test_route_exists()