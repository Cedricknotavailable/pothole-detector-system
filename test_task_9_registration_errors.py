"""
Test Task 9.3 and 9.4: Registration route field-specific error messages
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User
import json

def test_registration_empty_fields():
    """Test that empty fields show specific error messages"""
    with app.test_client() as client:
        response = client.post('/register', data={
            'username': '',
            'email': '',
            'password': ''
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Username is required' in data['errors']['username']
        assert 'Email is required' in data['errors']['email']
        assert 'Password is required' in data['errors']['password']
    
    print("✓ Empty field validation works correctly")

def test_registration_username_validation():
    """Test username validation rules"""
    with app.test_client() as client:
        # Test short username
        response = client.post('/register', data={
            'username': 'ab',
            'email': 'test@example.com',
            'password': 'ValidPass123'
        })
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Username must be at least 3 characters' in data['errors']['username']
    
    print("✓ Username length validation works correctly")

def test_registration_email_validation():
    """Test email validation rules"""
    with app.test_client() as client:
        # Test invalid email format
        response = client.post('/register', data={
            'username': 'testuser',
            'email': 'invalidemail',
            'password': 'ValidPass123'
        })
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Invalid email format' in data['errors']['email']
    
    print("✓ Email format validation works correctly")

def test_registration_password_validation():
    """Test password validation rules"""
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
        
        # Test password without uppercase
        response = client.post('/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'lowercase123'
        })
        data = json.loads(response.data)
        assert data['success'] == False
        assert any('uppercase' in err for err in data['errors']['password'])
        
        # Test password without lowercase
        response = client.post('/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'UPPERCASE123'
        })
        data = json.loads(response.data)
        assert data['success'] == False
        assert any('lowercase' in err for err in data['errors']['password'])
        
        # Test password without digit
        response = client.post('/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'NoDigitsHere'
        })
        data = json.loads(response.data)
        assert data['success'] == False
        assert any('number' in err for err in data['errors']['password'])
    
    print("✓ Password validation rules work correctly")

def test_registration_duplicate_username():
    """Test that duplicate username shows specific error"""
    with app.app_context():
        # Create a test user
        test_user = User.query.filter_by(username='existinguser').first()
        if not test_user:
            test_user = User(
                username='existinguser',
                email='existing@example.com',
                role='user',
                status='active'
            )
            test_user.set_password('Password123')
            db.session.add(test_user)
            db.session.commit()
    
    with app.test_client() as client:
        response = client.post('/register', data={
            'username': 'existinguser',
            'email': 'newemail@example.com',
            'password': 'ValidPass123'
        })
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Username already exists' in data['errors']['username']
    
    print("✓ Duplicate username validation works correctly")

def test_registration_duplicate_email():
    """Test that duplicate email shows specific error"""
    with app.app_context():
        # Ensure test user exists
        test_user = User.query.filter_by(email='existing@example.com').first()
        if not test_user:
            test_user = User(
                username='existinguser2',
                email='existing@example.com',
                role='user',
                status='active'
            )
            test_user.set_password('Password123')
            db.session.add(test_user)
            db.session.commit()
    
    with app.test_client() as client:
        response = client.post('/register', data={
            'username': 'newusername',
            'email': 'existing@example.com',
            'password': 'ValidPass123'
        })
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Email already registered' in data['errors']['email']
    
    print("✓ Duplicate email validation works correctly")

def test_registration_multiple_password_errors():
    """Test that multiple password errors are shown"""
    with app.test_client() as client:
        response = client.post('/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'bad'
        })
        data = json.loads(response.data)
        assert data['success'] == False
        # Should have multiple password errors
        assert len(data['errors']['password']) > 1
    
    print("✓ Multiple password errors shown correctly")

if __name__ == '__main__':
    print("Testing Task 9.3 and 9.4: Registration field-specific errors\n")
    
    test_registration_empty_fields()
    test_registration_username_validation()
    test_registration_email_validation()
    test_registration_password_validation()
    test_registration_duplicate_username()
    test_registration_duplicate_email()
    test_registration_multiple_password_errors()
    
    print("\n✅ All registration error tests passed!")
