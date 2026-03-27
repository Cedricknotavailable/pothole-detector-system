"""
Bug Condition Exploration Test for Notification Routes Mobile Fix

This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

Property 1: Bug Condition - Notification Popup Display on My Reports and Analytics

The test encodes the expected behavior and will validate the fix when it passes after implementation.
"""

import pytest
from flask import Flask
from bs4 import BeautifulSoup
import sys
import os

# Add parent directory to path to import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User


class TestBugConditionNotificationRoutes:
    """
    Test suite to surface counterexamples demonstrating the notification routes bug.
    
    Expected to FAIL on unfixed code:
    - My Reports: clicking bell navigates to broken route instead of showing popup
    - Analytics: clicking bell does nothing, no popup appears
    - Direct route: accessing /notifications raises TemplateNotFound error
    - Missing HTML: notifPopup div not found on My Reports and Analytics pages
    """
    
    @pytest.fixture
    def client(self):
        """Create test client with in-memory database"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        
        with app.test_client() as client:
            with app.app_context():
                db.create_all()
                
                # Create test user (regular user for my-reports)
                user = User(username='testuser', email='test@example.com', role='user', status='active')
                user.set_password('password123')
                db.session.add(user)
                
                # Create admin user for analytics page
                admin = User(username='adminuser', email='admin@example.com', role='admin', status='active')
                admin.set_password('admin123')
                db.session.add(admin)
                
                db.session.commit()
                
                yield client
                
                db.session.remove()
                db.drop_all()
    
    def login(self, client, username='testuser', password='password123'):
        """Helper to log in a user and establish session"""
        with client.session_transaction() as sess:
            # Find the user
            user = User.query.filter_by(username=username).first()
            if user:
                sess['user_id'] = user.id
                sess['csrf_token'] = 'test_token'
        return client
    
    def test_my_reports_notification_popup_structure_exists(self, client):
        """
        Test that My Reports page has notification popup HTML structure.
        
        EXPECTED TO FAIL on unfixed code: notifPopup div not found
        """
        self.login(client)
        response = client.get('/my-reports')
        assert response.status_code == 200
        
        html = response.data.decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check for notification button
        notif_btn = soup.find(id='notifBtn')
        assert notif_btn is not None, "Notification button (id='notifBtn') not found on My Reports page"
        
        # Check for notification popup structure (WILL FAIL on unfixed code)
        notif_popup = soup.find(id='notifPopup')
        assert notif_popup is not None, "Notification popup (id='notifPopup') not found on My Reports page - EXPECTED FAILURE on unfixed code"
        
        # Check for notification list container
        notif_list = soup.find(id='notifList')
        assert notif_list is not None, "Notification list (id='notifList') not found on My Reports page"
        
        # Check for mark all read button
        mark_all_btn = soup.find(id='markAllReadBtn')
        assert mark_all_btn is not None, "Mark all read button (id='markAllReadBtn') not found on My Reports page"
    
    def test_my_reports_notification_uses_button_not_link(self, client):
        """
        Test that My Reports page uses button for notifications, not a link to /notifications.
        
        EXPECTED TO FAIL on unfixed code: Uses <a href="/notifications"> instead of button
        """
        self.login(client)
        response = client.get('/my-reports')
        assert response.status_code == 200
        
        html = response.data.decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check that notification bell is a button, not a link
        notif_btn = soup.find(id='notifBtn')
        assert notif_btn is not None, "Notification button not found"
        assert notif_btn.name == 'button', f"Notification bell should be a <button>, not <{notif_btn.name}> - EXPECTED FAILURE on unfixed code"
        
        # Verify no link to /notifications in the notification area
        notif_links = soup.find_all('a', href='/notifications')
        # Filter out any links that might be in navigation
        header_notif_links = [link for link in notif_links if link.find_parent('header')]
        assert len(header_notif_links) == 0, f"Found {len(header_notif_links)} link(s) to /notifications in header - should use popup instead"
    
    def test_analytics_notification_popup_structure_exists(self, client):
        """
        Test that Analytics page has notification popup HTML structure.
        
        EXPECTED TO FAIL on unfixed code: notifPopup div not found
        """
        self.login(client, username='adminuser', password='admin123')
        response = client.get('/analytics')
        assert response.status_code == 200
        
        html = response.data.decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check for notification button
        notif_btn = soup.find(id='notifBtn')
        assert notif_btn is not None, "Notification button (id='notifBtn') not found on Analytics page"
        
        # Check for notification popup structure (WILL FAIL on unfixed code)
        notif_popup = soup.find(id='notifPopup')
        assert notif_popup is not None, "Notification popup (id='notifPopup') not found on Analytics page - EXPECTED FAILURE on unfixed code"
        
        # Check for notification list container
        notif_list = soup.find(id='notifList')
        assert notif_list is not None, "Notification list (id='notifList') not found on Analytics page"
        
        # Check for mark all read button
        mark_all_btn = soup.find(id='markAllReadBtn')
        assert mark_all_btn is not None, "Mark all read button (id='markAllReadBtn') not found on Analytics page"
    
    def test_notifications_route_should_not_exist(self, client):
        """
        Test that /notifications route does not exist (should return 404).
        
        The popup-based approach doesn't need a dedicated notifications page.
        EXPECTED TO FAIL on unfixed code: Route exists and tries to render missing template
        """
        self.login(client)
        
        # Try to access /notifications route
        response = client.get('/notifications')
        
        # Should return 404 (route doesn't exist) after fix
        # On unfixed code, will return 500 (TemplateNotFound error)
        assert response.status_code == 404, f"Expected 404 for /notifications route, got {response.status_code} - EXPECTED FAILURE on unfixed code"
    
    def test_my_reports_has_notification_javascript(self, client):
        """
        Test that My Reports page has JavaScript implementation for notifications.
        
        EXPECTED TO FAIL on unfixed code: JavaScript not present
        """
        self.login(client)
        response = client.get('/my-reports')
        assert response.status_code == 200
        
        html = response.data.decode('utf-8')
        
        # Check for key JavaScript functions
        assert 'fetchNotifications' in html, "fetchNotifications function not found in My Reports page JavaScript"
        assert 'handleNotifClick' in html, "handleNotifClick function not found in My Reports page JavaScript"
        assert '/notifications/unread' in html, "API endpoint /notifications/unread not referenced in JavaScript"
        assert '/notifications/mark-read/' in html, "API endpoint /notifications/mark-read/ not referenced in JavaScript"
        assert '/notifications/mark-all-read' in html, "API endpoint /notifications/mark-all-read not referenced in JavaScript"
    
    def test_analytics_has_notification_javascript(self, client):
        """
        Test that Analytics page has JavaScript implementation for notifications.
        
        EXPECTED TO FAIL on unfixed code: JavaScript not present
        """
        self.login(client, username='adminuser', password='admin123')
        response = client.get('/analytics')
        assert response.status_code == 200
        
        html = response.data.decode('utf-8')
        
        # Check for key JavaScript functions
        assert 'fetchNotifications' in html, "fetchNotifications function not found in Analytics page JavaScript - EXPECTED FAILURE on unfixed code"
        assert 'handleNotifClick' in html, "handleNotifClick function not found in Analytics page JavaScript"
        assert '/notifications/unread' in html, "API endpoint /notifications/unread not referenced in JavaScript"
        assert '/notifications/mark-read/' in html, "API endpoint /notifications/mark-read/ not referenced in JavaScript"
        assert '/notifications/mark-all-read' in html, "API endpoint /notifications/mark-all-read not referenced in JavaScript"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
