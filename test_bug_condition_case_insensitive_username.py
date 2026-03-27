"""
Bug Condition Exploration Test - Case-Insensitive Username Login

**Validates: Requirements 1.1, 1.3, 2.1, 2.2**

This test demonstrates the bug exists on UNFIXED code.
The test encodes the EXPECTED behavior (case-insensitive username authentication).

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
When the code is fixed, this same test will PASS, confirming the fix works.

Bug Condition:
- User registers with a specific username casing (e.g., "TestUser")
- User attempts to login with different casing (e.g., "testuser", "TESTUSER")
- CURRENT BEHAVIOR (BUG): Login fails with "Username or email not found"
- EXPECTED BEHAVIOR (FIX): Login succeeds with case-insensitive matching

This test uses a scoped property-based approach to ensure reproducibility
by testing specific concrete failing cases that demonstrate the bug.
"""

import pytest
import os
import sys
from werkzeug.security import generate_password_hash

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app, db, User


@pytest.fixture
def client():
    """Create test client with isolated database"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()


def test_bug_condition_username_case_variations(client):
    """
    Property 1: Bug Condition - Case-Insensitive Username Authentication
    
    **Validates: Requirements 1.1, 1.3, 2.1, 2.2**
    
    Test that username lookups with different casing work correctly.
    This test encodes the EXPECTED behavior.
    
    EXPECTED OUTCOME ON UNFIXED CODE: FAIL (proves bug exists)
    EXPECTED OUTCOME ON FIXED CODE: PASS (confirms fix works)
    """
    
    # Single test case: Register "TestUser", login with "testuser"
    with app.app_context():
        user = User(
            username='TestUser',
            email='testuser@example.com',
            role='user',
            status='active',
            password_hash=generate_password_hash('Password123!')
        )
        db.session.add(user)
        db.session.commit()
    
    # Attempt login with lowercase username
    response = client.post('/login', data={
        'username': 'testuser',  # Different casing than registered "TestUser"
        'password': 'Password123!'
    }, follow_redirects=False)
    
    # EXPECTED BEHAVIOR: Login should succeed (redirect to map or index)
    # ON UNFIXED CODE: This will fail with "Username or email not found"
    
    # Debug: Print response data to see the error message
    if response.status_code == 200:
        print(f"\n[COUNTEREXAMPLE] Login with 'testuser' when registered as 'TestUser'")
        print(f"Status Code: {response.status_code} (expected 302)")
        print(f"Response contains 'Username or email not found': {'Username or email not found' in response.get_data(as_text=True)}")
    
    assert response.status_code == 302, \
        f"Expected redirect (302) for successful login, got {response.status_code}. " \
        f"Bug confirmed: Username lookup is case-sensitive."
    assert response.location in ['/map', '/index'], \
        f"Expected redirect to /map or /index, got {response.location}"
    
    # Verify session was created
    with client.session_transaction() as sess:
        assert 'user_id' in sess, "Expected user_id in session after successful login"


def test_bug_condition_email_already_case_insensitive(client):
    """
    Verify that email authentication is already case-insensitive (baseline).
    
    This test should PASS on both unfixed and fixed code, confirming that
    email authentication already works correctly with case variations.
    """
    
    with app.app_context():
        user = User(
            username='EmailUser',
            email='test@example.com',
            role='user',
            status='active',
            password_hash=generate_password_hash('Email123!')
        )
        db.session.add(user)
        db.session.commit()
    
    # Test email with different casing
    response = client.post('/login', data={
        'username': 'TEST@EXAMPLE.COM',  # Different casing than registered
        'password': 'Email123!'
    }, follow_redirects=False)
    
    # Email authentication should already work (case-insensitive)
    assert response.status_code == 302, \
        f"Email authentication should be case-insensitive, got {response.status_code}"
    assert response.location in ['/map', '/index'], \
        f"Expected redirect to /map or /index, got {response.location}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
