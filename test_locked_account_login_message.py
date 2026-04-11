#!/usr/bin/env python3
"""Test that locked accounts show appropriate error messages on login."""

from app import app, db, User
from werkzeug.security import generate_password_hash

def test_locked_account_false_reports():
    """Test that locked accounts due to false reports show detailed message."""
    print("\n" + "="*70)
    print("TEST: Locked Account Login Message (False Reports)")
    print("="*70)
    
    with app.test_client() as client:
        with app.app_context():
            # Clean up any existing test user
            existing = User.query.filter_by(username='locked_test_user').first()
            if existing:
                db.session.delete(existing)
                db.session.commit()
            
            # Create a locked user with false reports
            locked_user = User(
                username='locked_test_user',
                email='locked@test.com',
                role='user',
                status='locked',
                false_reports_count=5,
                password_hash=generate_password_hash('TestPass123!')
            )
            db.session.add(locked_user)
            db.session.commit()
            
            print(f"\n✓ Created locked test user with {locked_user.false_reports_count} false reports")
        
        # Attempt to login
        response = client.post('/login', data={
            'username': 'locked_test_user',
            'password': 'TestPass123!'
        }, follow_redirects=False)
        
        content = response.get_data(as_text=True)
        
        # Verify response
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Login blocked (status 200, no redirect)")
        
        # Check for key message components
        checks = [
            ('Account Permanently Blocked', 'Permanent blocking mentioned'),
            ('5 false report', 'False report count shown'),
            ('final and non-negotiable', 'Non-negotiable language present'),
            ('Terms of Service', 'ToS violation mentioned'),
            ('community trust', 'Community impact mentioned')
        ]
        
        for phrase, description in checks:
            if phrase in content:
                print(f"✓ {description}: '{phrase}'")
            else:
                print(f"✗ MISSING: {description}")
                assert False, f"Missing required phrase: {phrase}"
        
        # Verify error styling is applied
        assert 'input-error' in content, "Error styling should be applied"
        assert 'error-message' in content, "Error message class should be present"
        print("✓ Error styling applied correctly")
        
        print("\n" + "="*70)
        print("✓ ALL CHECKS PASSED")
        print("="*70)


def test_locked_account_no_false_reports():
    """Test that locked accounts without false reports show generic message."""
    print("\n" + "="*70)
    print("TEST: Locked Account Login Message (Generic)")
    print("="*70)
    
    with app.test_client() as client:
        with app.app_context():
            # Clean up any existing test user
            existing = User.query.filter_by(username='locked_generic_user').first()
            if existing:
                db.session.delete(existing)
                db.session.commit()
            
            # Create a locked user without false reports
            locked_user = User(
                username='locked_generic_user',
                email='locked_generic@test.com',
                role='user',
                status='locked',
                false_reports_count=0,
                password_hash=generate_password_hash('TestPass123!')
            )
            db.session.add(locked_user)
            db.session.commit()
            
            print(f"\n✓ Created locked test user with {locked_user.false_reports_count} false reports")
        
        # Attempt to login
        response = client.post('/login', data={
            'username': 'locked_generic_user',
            'password': 'TestPass123!'
        }, follow_redirects=False)
        
        content = response.get_data(as_text=True)
        
        # Verify response
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Login blocked (status 200, no redirect)")
        
        # Check for generic message
        assert 'Your account is locked' in content, "Generic locked message should be shown"
        assert 'contact an administrator' in content, "Admin contact instruction should be shown"
        print("✓ Generic locked account message shown")
        
        # Should NOT show false report details
        assert 'false report' not in content.lower(), "Should not mention false reports"
        assert 'permanently' not in content.lower(), "Should not mention permanent blocking"
        print("✓ False report details not shown (as expected)")
        
        print("\n" + "="*70)
        print("✓ ALL CHECKS PASSED")
        print("="*70)


def test_normal_login_still_works():
    """Test that normal users can still login successfully."""
    print("\n" + "="*70)
    print("TEST: Normal Login Still Works")
    print("="*70)
    
    with app.test_client() as client:
        with app.app_context():
            # Clean up any existing test user
            existing = User.query.filter_by(username='normal_test_user').first()
            if existing:
                db.session.delete(existing)
                db.session.commit()
            
            # Create a normal active user
            normal_user = User(
                username='normal_test_user',
                email='normal@test.com',
                role='user',
                status='active',
                false_reports_count=0,
                password_hash=generate_password_hash('TestPass123!')
            )
            db.session.add(normal_user)
            db.session.commit()
            
            print("\n✓ Created normal active test user")
        
        # Attempt to login
        response = client.post('/login', data={
            'username': 'normal_test_user',
            'password': 'TestPass123!'
        }, follow_redirects=False)
        
        # Verify successful login (redirect)
        assert response.status_code == 302, f"Expected redirect (302), got {response.status_code}"
        print("✓ Login successful (redirected)")
        
        # Verify session was created
        with client.session_transaction() as sess:
            assert 'user_id' in sess, "User ID should be in session"
            print(f"✓ Session created for user_id: {sess['user_id']}")
        
        print("\n" + "="*70)
        print("✓ ALL CHECKS PASSED")
        print("="*70)


if __name__ == '__main__':
    try:
        test_locked_account_false_reports()
        test_locked_account_no_false_reports()
        test_normal_login_still_works()
        
        print("\n" + "="*70)
        print("✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("="*70)
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
