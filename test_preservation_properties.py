"""
Preservation Property Tests - Existing Authentication Behavior

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

These tests capture the EXISTING behavior on UNFIXED code for non-buggy inputs.
They ensure that the fix does NOT introduce regressions.

IMPORTANT: Follow observation-first methodology
- These tests are written AFTER observing behavior on UNFIXED code
- They capture the baseline behavior that must be preserved
- EXPECTED OUTCOME ON UNFIXED CODE: PASS (confirms baseline behavior)
- EXPECTED OUTCOME ON FIXED CODE: PASS (confirms no regressions)

Property 2: Preservation - Existing Authentication Behavior
For any login attempt that does NOT involve username casing variations,
the system should continue to behave exactly as before.
"""

import pytest
import os
import sys
from werkzeug.security import generate_password_hash
from hypothesis import given, strategies as st, settings, Phase, HealthCheck

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


# ============================================================================
# Property 2.1: Email Login Preservation (Requirement 3.1)
# ============================================================================

def test_preservation_email_case_insensitive(client):
    """
    Property 2.1: Email authentication continues case-insensitive matching
    
    **Validates: Requirement 3.1**
    
    Email-based login should continue to work with case variations.
    This behavior already exists and must be preserved.
    """
    
    with app.app_context():
        user = User(
            username='emailuser',
            email='user@example.com',
            role='user',
            status='active',
            password_hash=generate_password_hash('EmailPass123!')
        )
        db.session.add(user)
        db.session.commit()
    
    # Test various email case variations
    email_variations = [
        'user@example.com',      # Original
        'USER@EXAMPLE.COM',      # All uppercase
        'User@Example.Com',      # Mixed case
        'uSeR@eXaMpLe.CoM'       # Random mixed case
    ]
    
    for email_variant in email_variations:
        response = client.post('/login', data={
            'username': email_variant,
            'password': 'EmailPass123!'
        }, follow_redirects=False)
        
        assert response.status_code == 302, \
            f"Email login with '{email_variant}' should succeed (case-insensitive)"
        assert response.location in ['/map', '/index'], \
            f"Expected redirect to /map or /index for email '{email_variant}'"


@given(
    email_local=st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=65, max_codepoint=122),
        min_size=3,
        max_size=10
    ).filter(lambda x: x and not x.isspace()),
    email_domain=st.sampled_from(['example.com', 'test.org', 'demo.net'])
)
@settings(max_examples=20, phases=[Phase.generate], suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
def test_preservation_email_property_based(client, email_local, email_domain):
    """
    Property-based test: Email authentication is case-insensitive
    
    **Validates: Requirement 3.1**
    
    For any valid email, login should succeed regardless of casing.
    """
    
    original_email = f"{email_local}@{email_domain}".lower()
    
    with app.app_context():
        # Clear any existing users
        User.query.delete()
        
        user = User(
            username=f"user_{email_local[:5]}",
            email=original_email,
            role='user',
            status='active',
            password_hash=generate_password_hash('TestPass123!')
        )
        db.session.add(user)
        db.session.commit()
    
    # Test with uppercase version
    uppercase_email = original_email.upper()
    response = client.post('/login', data={
        'username': uppercase_email,
        'password': 'TestPass123!'
    }, follow_redirects=False)
    
    assert response.status_code == 302, \
        f"Email login should be case-insensitive for '{original_email}' vs '{uppercase_email}'"


# ============================================================================
# Property 2.2: Incorrect Password Preservation (Requirement 3.2)
# ============================================================================

def test_preservation_incorrect_password(client):
    """
    Property 2.2: Incorrect password scenarios fail with appropriate error
    
    **Validates: Requirement 3.2**
    
    Wrong password should continue to return "Incorrect password" error.
    """
    
    with app.app_context():
        user = User(
            username='testuser',
            email='test@example.com',
            role='user',
            status='active',
            password_hash=generate_password_hash('CorrectPass123!')
        )
        db.session.add(user)
        db.session.commit()
    
    # Test with username
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'WrongPassword123!'
    }, follow_redirects=False)
    
    assert response.status_code == 200, "Incorrect password should not redirect"
    assert 'Incorrect password' in response.get_data(as_text=True), \
        "Should display 'Incorrect password' error"
    
    # Test with email
    response = client.post('/login', data={
        'username': 'test@example.com',
        'password': 'WrongPassword123!'
    }, follow_redirects=False)
    
    assert response.status_code == 200, "Incorrect password should not redirect"
    assert 'Incorrect password' in response.get_data(as_text=True), \
        "Should display 'Incorrect password' error"


@given(
    wrong_password=st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=33, max_codepoint=126),
        min_size=8,
        max_size=20
    ).filter(lambda x: x != 'CorrectPass123!')
)
@settings(max_examples=15, phases=[Phase.generate], suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
def test_preservation_incorrect_password_property(client, wrong_password):
    """
    Property-based test: Any incorrect password fails with appropriate error
    
    **Validates: Requirement 3.2**
    """
    
    with app.app_context():
        # Clear existing users
        User.query.delete()
        
        user = User(
            username='propuser',
            email='prop@example.com',
            role='user',
            status='active',
            password_hash=generate_password_hash('CorrectPass123!')
        )
        db.session.add(user)
        db.session.commit()
    
    response = client.post('/login', data={
        'username': 'propuser',
        'password': wrong_password
    }, follow_redirects=False)
    
    assert response.status_code == 200, \
        f"Incorrect password '{wrong_password}' should not redirect"
    assert 'Incorrect password' in response.get_data(as_text=True), \
        f"Should display 'Incorrect password' error for '{wrong_password}'"


# ============================================================================
# Property 2.3: Non-Existent User Preservation (Requirement 3.2)
# ============================================================================

def test_preservation_nonexistent_user(client):
    """
    Property 2.3: Non-existent username/email returns appropriate error
    
    **Validates: Requirement 3.2**
    
    Login attempts with non-existent accounts should continue to fail
    with "Username or email not found" error.
    """
    
    # No users in database
    
    # Test with non-existent username
    response = client.post('/login', data={
        'username': 'nonexistentuser',
        'password': 'SomePassword123!'
    }, follow_redirects=False)
    
    assert response.status_code == 200, "Non-existent user should not redirect"
    assert 'Username or email not found' in response.get_data(as_text=True), \
        "Should display 'Username or email not found' error"
    
    # Test with non-existent email
    response = client.post('/login', data={
        'username': 'nonexistent@example.com',
        'password': 'SomePassword123!'
    }, follow_redirects=False)
    
    assert response.status_code == 200, "Non-existent email should not redirect"
    assert 'Username or email not found' in response.get_data(as_text=True), \
        "Should display 'Username or email not found' error"


@given(
    fake_username=st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=65, max_codepoint=122),
        min_size=5,
        max_size=15
    ).filter(lambda x: x and not x.isspace())
)
@settings(max_examples=15, phases=[Phase.generate], suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
def test_preservation_nonexistent_user_property(client, fake_username):
    """
    Property-based test: Any non-existent username fails appropriately
    
    **Validates: Requirement 3.2**
    """
    
    # Ensure no users exist
    with app.app_context():
        User.query.delete()
        db.session.commit()
    
    response = client.post('/login', data={
        'username': fake_username,
        'password': 'AnyPassword123!'
    }, follow_redirects=False)
    
    assert response.status_code == 200, \
        f"Non-existent user '{fake_username}' should not redirect"
    assert 'Username or email not found' in response.get_data(as_text=True), \
        f"Should display 'Username or email not found' for '{fake_username}'"


# ============================================================================
# Property 2.4: Locked Account Preservation (Requirement 3.3)
# ============================================================================

def test_preservation_locked_account(client):
    """
    Property 2.4: Locked account handling continues to work
    
    **Validates: Requirement 3.3**
    
    Locked accounts should continue to display lock message.
    """
    
    with app.app_context():
        user = User(
            username='lockeduser',
            email='locked@example.com',
            role='user',
            status='locked',
            password_hash=generate_password_hash('LockedPass123!')
        )
        db.session.add(user)
        db.session.commit()
    
    # Test with username
    response = client.post('/login', data={
        'username': 'lockeduser',
        'password': 'LockedPass123!'
    }, follow_redirects=False)
    
    assert response.status_code == 200, "Locked account should not redirect"
    assert 'Your account is locked' in response.get_data(as_text=True), \
        "Should display locked account message"
    
    # Test with email
    response = client.post('/login', data={
        'username': 'locked@example.com',
        'password': 'LockedPass123!'
    }, follow_redirects=False)
    
    assert response.status_code == 200, "Locked account should not redirect"
    assert 'Your account is locked' in response.get_data(as_text=True), \
        "Should display locked account message"


# ============================================================================
# Property 2.5: Suspended Account Preservation (Requirement 3.3)
# ============================================================================

def test_preservation_suspended_account(client):
    """
    Property 2.5: Suspended account handling continues to work
    
    **Validates: Requirement 3.3**
    
    Suspended accounts should continue to display suspension message.
    """
    
    with app.app_context():
        user = User(
            username='suspendeduser',
            email='suspended@example.com',
            role='user',
            status='suspended',
            password_hash=generate_password_hash('SuspendedPass123!')
        )
        db.session.add(user)
        db.session.commit()
    
    # Test with username
    response = client.post('/login', data={
        'username': 'suspendeduser',
        'password': 'SuspendedPass123!'
    }, follow_redirects=False)
    
    assert response.status_code == 200, "Suspended account should not redirect"
    response_text = response.get_data(as_text=True)
    assert 'Your account is suspended' in response_text, \
        "Should display suspended account message"
    
    # Test with email
    response = client.post('/login', data={
        'username': 'suspended@example.com',
        'password': 'SuspendedPass123!'
    }, follow_redirects=False)
    
    assert response.status_code == 200, "Suspended account should not redirect"
    response_text = response.get_data(as_text=True)
    assert 'Your account is suspended' in response_text, \
        "Should display suspended account message"


# ============================================================================
# Property 2.6: Empty Field Validation Preservation (Requirement 3.4)
# ============================================================================

def test_preservation_empty_username(client):
    """
    Property 2.6a: Empty username field validation continues to work
    
    **Validates: Requirement 3.4**
    
    Empty username should continue to return field-specific error.
    """
    
    response = client.post('/login', data={
        'username': '',
        'password': 'SomePassword123!'
    }, follow_redirects=False)
    
    assert response.status_code == 200, "Empty username should not redirect"
    assert 'Username or email is required' in response.get_data(as_text=True), \
        "Should display 'Username or email is required' error"


def test_preservation_empty_password(client):
    """
    Property 2.6b: Empty password field validation continues to work
    
    **Validates: Requirement 3.4**
    
    Empty password should continue to return field-specific error.
    """
    
    response = client.post('/login', data={
        'username': 'someuser',
        'password': ''
    }, follow_redirects=False)
    
    assert response.status_code == 200, "Empty password should not redirect"
    assert 'Password is required' in response.get_data(as_text=True), \
        "Should display 'Password is required' error"


def test_preservation_both_fields_empty(client):
    """
    Property 2.6c: Both fields empty validation continues to work
    
    **Validates: Requirement 3.4**
    
    Both fields empty should continue to return both field errors.
    """
    
    response = client.post('/login', data={
        'username': '',
        'password': ''
    }, follow_redirects=False)
    
    assert response.status_code == 200, "Empty fields should not redirect"
    response_text = response.get_data(as_text=True)
    assert 'Username or email is required' in response_text, \
        "Should display username error"
    assert 'Password is required' in response_text, \
        "Should display password error"


# ============================================================================
# Property 2.7: Successful Login Preservation (Requirement 3.5)
# ============================================================================

def test_preservation_successful_login_exact_match(client):
    """
    Property 2.7: Successful login with exact username match continues to work
    
    **Validates: Requirement 3.5**
    
    Login with exact username match should continue to work as before.
    """
    
    with app.app_context():
        user = User(
            username='ExactUser',
            email='exact@example.com',
            role='user',
            status='active',
            password_hash=generate_password_hash('ExactPass123!')
        )
        db.session.add(user)
        db.session.commit()
    
    # Login with exact username match
    response = client.post('/login', data={
        'username': 'ExactUser',  # Exact match
        'password': 'ExactPass123!'
    }, follow_redirects=False)
    
    assert response.status_code == 302, \
        "Exact username match should succeed"
    assert response.location in ['/map', '/index'], \
        f"Expected redirect to /map or /index, got {response.location}"
    
    # Verify session was created
    with client.session_transaction() as sess:
        assert 'user_id' in sess, \
            "Expected user_id in session after successful login"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
