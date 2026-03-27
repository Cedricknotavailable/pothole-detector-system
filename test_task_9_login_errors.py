"""
Test Task 9.1 and 9.2: Login route field-specific error messages
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User
import tempfile

def test_login_empty_fields():
    """Test that empty fields show specific error messages"""
    with app.test_client() as client:
        # Test empty username
        response = client.post('/login', data={
            'username': '',
            'password': 'somepassword'
        })
        assert response.status_code == 200
        assert b'Username or email is required' in response.data
        
        # Test empty password
        response = client.post('/login', data={
            'username': 'testuser',
            'password': ''
        })
        assert response.status_code == 200
        assert b'Password is required' in response.data
        
        # Test both empty
        response = client.post('/login', data={
            'username': '',
            'password': ''
        })
        assert response.status_code == 200
        assert b'Username or email is required' in response.data
        assert b'Password is required' in response.data
    
    print("✓ Empty field validation works correctly")

def test_login_user_not_found():
    """Test that non-existent user shows specific error"""
    with app.test_client() as client:
        response = client.post('/login', data={
            'username': 'nonexistentuser123',
            'password': 'somepassword'
        })
        assert response.status_code == 200
        assert b'Username or email not found' in response.data
    
    print("✓ User not found error works correctly")

def test_login_incorrect_password():
    """Test that incorrect password shows specific error"""
    with app.app_context():
        # Create a test user
        test_user = User.query.filter_by(username='testuser_login').first()
        if not test_user:
            test_user = User(
                username='testuser_login',
                email='testlogin@example.com',
                role='user',
                status='active'
            )
            test_user.set_password('CorrectPassword123')
            db.session.add(test_user)
            db.session.commit()
    
    with app.test_client() as client:
        response = client.post('/login', data={
            'username': 'testuser_login',
            'password': 'WrongPassword123'
        })
        assert response.status_code == 200
        assert b'Incorrect password' in response.data
    
    print("✓ Incorrect password error works correctly")

def test_login_preserves_username():
    """Test that username is preserved on error"""
    with app.test_client() as client:
        response = client.post('/login', data={
            'username': 'testuser123',
            'password': ''
        })
        assert response.status_code == 200
        assert b'testuser123' in response.data
    
    print("✓ Username preservation works correctly")

def test_login_template_has_error_classes():
    """Test that template includes error styling classes"""
    with app.test_client() as client:
        response = client.post('/login', data={
            'username': '',
            'password': 'test'
        })
        assert response.status_code == 200
        assert b'input-error' in response.data
        assert b'field-error' in response.data
        assert b'error-message' in response.data
    
    print("✓ Template error classes present")

if __name__ == '__main__':
    print("Testing Task 9.1 and 9.2: Login field-specific errors\n")
    
    test_login_empty_fields()
    test_login_user_not_found()
    test_login_incorrect_password()
    test_login_preserves_username()
    test_login_template_has_error_classes()
    
    print("\n✅ All login error tests passed!")
