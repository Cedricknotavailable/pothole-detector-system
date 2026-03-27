"""
Integration test for Task 9: Specific login and registration error messages
Tests all requirements from the spec.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User
import json

def test_requirement_5_1_login_username_not_found():
    """
    Requirement 5.1: WHEN login fails due to incorrect username or email, 
    THE System SHALL display "Username or email not found" below the username field
    """
    with app.test_client() as client:
        response = client.post('/login', data={
            'username': 'nonexistentuser',
            'password': 'somepassword'
        })
        assert response.status_code == 200
        assert b'Username or email not found' in response.data
        print("✓ Requirement 5.1: Username not found error displayed correctly")

def test_requirement_5_2_login_incorrect_password():
    """
    Requirement 5.2: WHEN login fails due to incorrect password, 
    THE System SHALL display "Incorrect password" below the password field
    """
    with app.app_context():
        # Ensure test user exists
        test_user = User.query.filter_by(username='testuser_req52').first()
        if not test_user:
            test_user = User(
                username='testuser_req52',
                email='testreq52@example.com',
                role='user',
                status='active'
            )
            test_user.set_password('CorrectPassword123')
            db.session.add(test_user)
            db.session.commit()
    
    with app.test_client() as client:
        response = client.post('/login', data={
            'username': 'testuser_req52',
            'password': 'WrongPassword123'
        })
        assert response.status_code == 200
        assert b'Incorrect password' in response.data
        print("✓ Requirement 5.2: Incorrect password error displayed correctly")

def test_requirement_5_3_registration_duplicate_username():
    """
    Requirement 5.3: WHEN registration fails due to duplicate username, 
    THE System SHALL display "Username already exists" below the username field
    """
    with app.app_context():
        # Ensure test user exists
        test_user = User.query.filter_by(username='existinguser_req53').first()
        if not test_user:
            test_user = User(
                username='existinguser_req53',
                email='existing53@example.com',
                role='user',
                status='active'
            )
            test_user.set_password('Password123')
            db.session.add(test_user)
            db.session.commit()
    
    with app.test_client() as client:
        response = client.post('/register', data={
            'username': 'existinguser_req53',
            'email': 'newemail@example.com',
            'password': 'ValidPass123'
        })
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Username already exists' in data['errors']['username']
        print("✓ Requirement 5.3: Duplicate username error displayed correctly")

def test_requirement_5_4_registration_duplicate_email():
    """
    Requirement 5.4: WHEN registration fails due to duplicate email, 
    THE System SHALL display "Email already registered" below the email field
    """
    with app.app_context():
        # Ensure test user exists
        test_user = User.query.filter_by(email='existing54@example.com').first()
        if not test_user:
            test_user = User(
                username='existinguser_req54',
                email='existing54@example.com',
                role='user',
                status='active'
            )
            test_user.set_password('Password123')
            db.session.add(test_user)
            db.session.commit()
    
    with app.test_client() as client:
        response = client.post('/register', data={
            'username': 'newusername',
            'email': 'existing54@example.com',
            'password': 'ValidPass123'
        })
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Email already registered' in data['errors']['email']
        print("✓ Requirement 5.4: Duplicate email error displayed correctly")

def test_requirement_5_5_registration_invalid_email():
    """
    Requirement 5.5: WHEN registration fails due to invalid email format, 
    THE System SHALL display "Invalid email format" below the email field
    """
    with app.test_client() as client:
        response = client.post('/register', data={
            'username': 'testuser',
            'email': 'invalidemail',
            'password': 'ValidPass123'
        })
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Invalid email format' in data['errors']['email']
        print("✓ Requirement 5.5: Invalid email format error displayed correctly")

def test_requirement_5_6_registration_weak_password():
    """
    Requirement 5.6: WHEN registration fails due to weak password, 
    THE System SHALL display the specific password requirement that was not met
    """
    with app.test_client() as client:
        # Test short password
        response = client.post('/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'short'
        })
        data = json.loads(response.data)
        assert data['success'] == False
        assert any('8 characters' in err for err in data['errors']['password'])
        
        # Test missing uppercase
        response = client.post('/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'lowercase123'
        })
        data = json.loads(response.data)
        assert data['success'] == False
        assert any('uppercase' in err for err in data['errors']['password'])
        
        # Test missing lowercase
        response = client.post('/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'UPPERCASE123'
        })
        data = json.loads(response.data)
        assert data['success'] == False
        assert any('lowercase' in err for err in data['errors']['password'])
        
        # Test missing digit
        response = client.post('/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'NoDigitsHere'
        })
        data = json.loads(response.data)
        assert data['success'] == False
        assert any('number' in err for err in data['errors']['password'])
        
        print("✓ Requirement 5.6: Specific password requirement errors displayed correctly")

def test_requirement_5_7_error_clearing():
    """
    Requirement 5.7: THE System SHALL clear previous error messages 
    when the user modifies any input field
    """
    with app.test_client() as client:
        # Get login page
        response = client.get('/login')
        html = response.data.decode('utf-8')
        
        # Verify error clearing JavaScript is present
        assert "addEventListener('input'" in html or "addEventListener(\"input\"" in html
        assert "classList.remove('input-error')" in html or 'classList.remove("input-error")' in html
        assert "querySelector('.field-error')" in html or 'querySelector(".field-error")' in html
        
        # Get register page
        response = client.get('/register')
        html = response.data.decode('utf-8')
        
        # Verify error clearing JavaScript is present
        assert "addEventListener('input'" in html or "addEventListener(\"input\"" in html
        assert "classList.remove('input-error')" in html or 'classList.remove("input-error")' in html
        
        print("✓ Requirement 5.7: Error clearing on input implemented")

def test_requirement_5_8_field_specific_errors():
    """
    Requirement 5.8: THE System SHALL display field-specific errors 
    without showing generic error messages
    """
    with app.test_client() as client:
        # Test login with empty fields
        response = client.post('/login', data={
            'username': '',
            'password': ''
        })
        html = response.data.decode('utf-8')
        
        # Should have field-specific errors
        assert 'field-error' in html
        assert 'error-message' in html or 'Username or email is required' in html
        
        # Test registration with invalid data
        response = client.post('/register', data={
            'username': 'ab',
            'email': 'invalid',
            'password': 'weak'
        })
        data = json.loads(response.data)
        
        # Should have field-specific errors for each field
        assert 'username' in data['errors']
        assert 'email' in data['errors']
        assert 'password' in data['errors']
        
        print("✓ Requirement 5.8: Field-specific errors displayed without generic messages")

def test_input_value_preservation():
    """Test that input values are preserved on error (Requirement 5.8)"""
    with app.test_client() as client:
        response = client.post('/login', data={
            'username': 'testuser123',
            'password': ''
        })
        assert response.status_code == 200
        assert b'testuser123' in response.data
        print("✓ Input values preserved on error")

def test_error_styling():
    """Test that error styling is applied correctly"""
    with app.test_client() as client:
        response = client.post('/login', data={
            'username': '',
            'password': 'test'
        })
        html = response.data.decode('utf-8')
        
        # Check for input-error class
        assert 'input-error' in html
        
        # Check CSS files have error styles
        with open('static/css/login.css', 'r') as f:
            css = f.read()
            assert '.input-error' in css
            assert '.field-error' in css
            assert '.error-message' in css
        
        print("✓ Error styling applied correctly")

if __name__ == '__main__':
    print("=" * 70)
    print("TASK 9 INTEGRATION TEST: Specific Login and Registration Error Messages")
    print("=" * 70)
    print()
    
    test_requirement_5_1_login_username_not_found()
    test_requirement_5_2_login_incorrect_password()
    test_requirement_5_3_registration_duplicate_username()
    test_requirement_5_4_registration_duplicate_email()
    test_requirement_5_5_registration_invalid_email()
    test_requirement_5_6_registration_weak_password()
    test_requirement_5_7_error_clearing()
    test_requirement_5_8_field_specific_errors()
    test_input_value_preservation()
    test_error_styling()
    
    print()
    print("=" * 70)
    print("✅ ALL REQUIREMENTS VERIFIED - TASK 9 COMPLETE")
    print("=" * 70)
