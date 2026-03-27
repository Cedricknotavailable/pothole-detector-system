"""
Test Task 9.5: Client-side error clearing functionality
This test verifies that the JavaScript code for clearing errors is present in the templates.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

def test_login_has_error_clearing_script():
    """Test that login template includes error clearing JavaScript"""
    with app.test_client() as client:
        response = client.get('/login')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        
        # Check for script tag
        assert '<script>' in html
        
        # Check for input event listener setup
        assert "addEventListener('input'" in html or "addEventListener(\"input\"" in html
        
        # Check for error class removal
        assert "classList.remove('input-error')" in html or 'classList.remove("input-error")' in html
        
        # Check for error div removal
        assert "querySelector('.field-error')" in html or 'querySelector(".field-error")' in html
        assert '.remove()' in html
    
    print("✓ Login template has error clearing JavaScript")

def test_register_has_error_clearing_script():
    """Test that register template includes error clearing JavaScript"""
    with app.test_client() as client:
        response = client.get('/register')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        
        # Check for script tag
        assert '<script>' in html
        
        # Check for input event listener setup
        assert "addEventListener('input'" in html or "addEventListener(\"input\"" in html
        
        # Check for error class removal
        assert "classList.remove('input-error')" in html or 'classList.remove("input-error")' in html
        
        # Check for error handling for username, email, password fields
        assert 'username' in html
        assert 'email' in html
        assert 'password' in html
    
    print("✓ Register template has error clearing JavaScript")

def test_login_error_display_structure():
    """Test that login errors are displayed with correct structure"""
    with app.test_client() as client:
        response = client.post('/login', data={
            'username': '',
            'password': ''
        })
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        
        # Check for error class on input
        assert 'input-error' in html
        
        # Check for field-error div
        assert 'field-error' in html
        
        # Check for error-message div
        assert 'error-message' in html
    
    print("✓ Login error display structure is correct")

def test_register_error_display_structure():
    """Test that register template has correct error display structure"""
    with app.test_client() as client:
        response = client.get('/register')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        
        # Check for error divs for each field
        assert 'usernameError' in html
        assert 'emailError' in html
        assert 'passwordError' in html
        
        # Check for field-error class
        assert 'field-error' in html
    
    print("✓ Register error display structure is correct")

def test_css_has_error_styles():
    """Test that CSS files include error styling"""
    # Test login.css
    with open('static/css/login.css', 'r') as f:
        login_css = f.read()
        assert '.input-error' in login_css
        assert '.field-error' in login_css
        assert '.error-message' in login_css
        assert 'border-color: #ef4444' in login_css or 'border-color:#ef4444' in login_css
    
    print("✓ Login CSS has error styles")
    
    # Test register.css
    with open('static/css/register.css', 'r') as f:
        register_css = f.read()
        assert '.input-error' in register_css
        assert '.field-error' in register_css
        assert 'border-color: #ef4444' in register_css or 'border-color:#ef4444' in register_css
    
    print("✓ Register CSS has error styles")

if __name__ == '__main__':
    print("Testing Task 9.5: Client-side error clearing\n")
    
    test_login_has_error_clearing_script()
    test_register_has_error_clearing_script()
    test_login_error_display_structure()
    test_register_error_display_structure()
    test_css_has_error_styles()
    
    print("\n✅ All client-side error clearing tests passed!")
