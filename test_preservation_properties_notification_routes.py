"""
Preservation Property Tests for Notification Routes Mobile Fix

Property 2: Preservation - Existing Notification Functionality on Settings and Users Pages

These tests verify that Settings and Users pages continue to work correctly after the fix.
EXPECTED TO PASS on both unfixed and fixed code (confirms no regressions).

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
"""

import pytest
from flask import Flask
from bs4 import BeautifulSoup
import sys
import os
import json
from hypothesis import given, strategies as st, settings, Phase, HealthCheck
from hypothesis import assume

# Add parent directory to path to import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Notification


class TestPreservationNotificationFunctionality:
    """
    Test suite to verify existing notification functionality is preserved.
    
    These tests should PASS on both unfixed and fixed code, confirming:
    - Settings page notification popup works correctly
    - Users page notification popup works correctly
    - API endpoints continue to function correctly
    - Badge display and polling continue to work
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
                
                # Create admin user for Settings and Users pages
                admin = User(username='adminuser', email='admin@example.com', role='admin', status='active')
                admin.set_password('admin123')
                db.session.add(admin)
                
                db.session.commit()
                
                yield client
                
                db.session.remove()
                db.drop_all()
    
    def login_admin(self, client):
        """Helper to log in admin user"""
        with client.session_transaction() as sess:
            user = User.query.filter_by(username='adminuser').first()
            if user:
                sess['user_id'] = user.id
                sess['csrf_token'] = 'test_token'
        return client
    
    # ========== Settings Page Preservation Tests ==========
    
    def test_settings_page_notification_popup_structure(self, client):
        """
        Test that Settings page has complete notification popup HTML structure.
        
        EXPECTED TO PASS on both unfixed and fixed code.
        """
        self.login_admin(client)
        response = client.get('/settings')
        assert response.status_code == 200
        
        html = response.data.decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check for notification button
        notif_btn = soup.find(id='notifBtn')
        assert notif_btn is not None, "Notification button (id='notifBtn') not found on Settings page"
        assert notif_btn.name == 'button', "Notification bell should be a button"
        
        # Check for notification badge
        notif_badge = soup.find(id='notifBadge')
        assert notif_badge is not None, "Notification badge (id='notifBadge') not found on Settings page"
        
        # Check for notification popup structure
        notif_popup = soup.find(id='notifPopup')
        assert notif_popup is not None, "Notification popup (id='notifPopup') not found on Settings page"
        
        # Check for notification list container
        notif_list = soup.find(id='notifList')
        assert notif_list is not None, "Notification list (id='notifList') not found on Settings page"
        
        # Check for mark all read button
        mark_all_btn = soup.find(id='markAllReadBtn')
        assert mark_all_btn is not None, "Mark all read button (id='markAllReadBtn') not found on Settings page"
    
    def test_settings_page_notification_javascript(self, client):
        """
        Test that Settings page has complete JavaScript implementation for notifications.
        
        EXPECTED TO PASS on both unfixed and fixed code.
        """
        self.login_admin(client)
        response = client.get('/settings')
        assert response.status_code == 200
        
        html = response.data.decode('utf-8')
        
        # Check for key JavaScript functions
        assert 'fetchNotifications' in html, "fetchNotifications function not found in Settings page"
        assert 'handleNotifClick' in html, "handleNotifClick function not found in Settings page"
        
        # Check for API endpoint references
        assert '/notifications/unread' in html, "API endpoint /notifications/unread not referenced"
        assert '/notifications/mark-read/' in html, "API endpoint /notifications/mark-read/ not referenced"
        assert '/notifications/mark-all-read' in html, "API endpoint /notifications/mark-all-read not referenced"
        
        # Check for polling setup (30-second interval)
        assert 'setInterval(fetchNotifications, 30000)' in html, "30-second polling not found in Settings page"
    
    # ========== Users Page Preservation Tests ==========
    
    def test_users_page_notification_popup_structure(self, client):
        """
        Test that Users page has complete notification popup HTML structure.
        
        EXPECTED TO PASS on both unfixed and fixed code.
        """
        self.login_admin(client)
        response = client.get('/users')
        assert response.status_code == 200
        
        html = response.data.decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check for notification button
        notif_btn = soup.find(id='notifBtn')
        assert notif_btn is not None, "Notification button (id='notifBtn') not found on Users page"
        assert notif_btn.name == 'button', "Notification bell should be a button"
        
        # Check for notification badge
        notif_badge = soup.find(id='notifBadge')
        assert notif_badge is not None, "Notification badge (id='notifBadge') not found on Users page"
        
        # Check for notification popup structure
        notif_popup = soup.find(id='notifPopup')
        assert notif_popup is not None, "Notification popup (id='notifPopup') not found on Users page"
        
        # Check for notification list container
        notif_list = soup.find(id='notifList')
        assert notif_list is not None, "Notification list (id='notifList') not found on Users page"
        
        # Check for mark all read button
        mark_all_btn = soup.find(id='markAllReadBtn')
        assert mark_all_btn is not None, "Mark all read button (id='markAllReadBtn') not found on Users page"
    
    def test_users_page_notification_javascript(self, client):
        """
        Test that Users page has complete JavaScript implementation for notifications.
        
        EXPECTED TO PASS on both unfixed and fixed code.
        """
        self.login_admin(client)
        response = client.get('/users')
        assert response.status_code == 200
        
        html = response.data.decode('utf-8')
        
        # Check for key JavaScript functions
        assert 'fetchNotifications' in html, "fetchNotifications function not found in Users page"
        assert 'handleNotifClick' in html, "handleNotifClick function not found in Users page"
        
        # Check for API endpoint references
        assert '/notifications/unread' in html, "API endpoint /notifications/unread not referenced"
        assert '/notifications/mark-read/' in html, "API endpoint /notifications/mark-read/ not referenced"
        assert '/notifications/mark-all-read' in html, "API endpoint /notifications/mark-all-read not referenced"
        
        # Check for polling setup (30-second interval)
        assert 'setInterval(fetchNotifications, 30000)' in html, "30-second polling not found in Users page"
    
    # ========== API Endpoint Preservation Tests ==========
    
    def test_notifications_unread_api_endpoint(self, client):
        """
        Test that /notifications/unread API endpoint continues to work correctly.
        
        EXPECTED TO PASS on both unfixed and fixed code.
        """
        self.login_admin(client)
        
        # Create test notifications
        with app.app_context():
            admin = User.query.filter_by(username='adminuser').first()
            notif1 = Notification(
                user_id=admin.id,
                title='Test Notification 1',
                message='This is a test notification',
                is_read=False
            )
            notif2 = Notification(
                user_id=admin.id,
                title='Test Notification 2',
                message='This is another test notification',
                is_read=False
            )
            db.session.add(notif1)
            db.session.add(notif2)
            db.session.commit()
        
        # Call API endpoint
        response = client.get('/notifications/unread')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'count' in data, "Response should contain 'count' field"
        assert 'items' in data, "Response should contain 'items' field"
        assert data['count'] == 2, f"Expected 2 unread notifications, got {data['count']}"
        assert len(data['items']) == 2, f"Expected 2 notification items, got {len(data['items'])}"
    
    def test_notifications_mark_read_api_endpoint(self, client):
        """
        Test that /notifications/mark-read/<id> API endpoint continues to work correctly.
        
        EXPECTED TO PASS on both unfixed and fixed code.
        """
        self.login_admin(client)
        
        # Create test notification
        with app.app_context():
            admin = User.query.filter_by(username='adminuser').first()
            notif = Notification(
                user_id=admin.id,
                title='Test Notification',
                message='This is a test notification',
                is_read=False
            )
            db.session.add(notif)
            db.session.commit()
            notif_id = notif.id
        
        # Mark notification as read
        response = client.post(f'/notifications/mark-read/{notif_id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data.get('success') is True, "Mark read should return success=True"
        
        # Verify notification is marked as read
        with app.app_context():
            notif = Notification.query.get(notif_id)
            assert notif.is_read is True, "Notification should be marked as read"
    
    def test_notifications_mark_all_read_api_endpoint(self, client):
        """
        Test that /notifications/mark-all-read API endpoint continues to work correctly.
        
        EXPECTED TO PASS on both unfixed and fixed code.
        """
        self.login_admin(client)
        
        # Create multiple test notifications
        with app.app_context():
            admin = User.query.filter_by(username='adminuser').first()
            for i in range(3):
                notif = Notification(
                    user_id=admin.id,
                    title=f'Test Notification {i+1}',
                    message=f'This is test notification {i+1}',
                    is_read=False
                )
                db.session.add(notif)
            db.session.commit()
        
        # Mark all notifications as read
        response = client.post('/notifications/mark-all-read')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data.get('success') is True, "Mark all read should return success=True"
        
        # Verify all notifications are marked as read
        with app.app_context():
            admin = User.query.filter_by(username='adminuser').first()
            unread_count = Notification.query.filter_by(user_id=admin.id, is_read=False).count()
            assert unread_count == 0, f"Expected 0 unread notifications, got {unread_count}"
    
    # ========== Property-Based Tests ==========
    
    @given(
        notification_count=st.integers(min_value=0, max_value=10),
        page=st.sampled_from(['settings', 'users'])
    )
    @settings(
        max_examples=20, 
        phases=[Phase.generate, Phase.target],
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    def test_property_notification_structure_consistent_across_pages(self, client, notification_count, page):
        """
        Property: Notification popup structure is consistent across Settings and Users pages.
        
        For any number of notifications (0-10) and any page (settings/users),
        the notification popup HTML structure should be present and consistent.
        
        **Validates: Requirements 3.1, 3.2**
        """
        self.login_admin(client)
        
        # Clean up any existing notifications from previous test runs
        with app.app_context():
            admin = User.query.filter_by(username='adminuser').first()
            Notification.query.filter_by(user_id=admin.id).delete()
            db.session.commit()
        
        # Create notifications
        with app.app_context():
            admin = User.query.filter_by(username='adminuser').first()
            for i in range(notification_count):
                notif = Notification(
                    user_id=admin.id,
                    title=f'Property Test Notification {i+1}',
                    message=f'Test message {i+1}',
                    is_read=False
                )
                db.session.add(notif)
            db.session.commit()
        
        # Get page
        response = client.get(f'/{page}')
        assert response.status_code == 200
        
        html = response.data.decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        
        # Verify structure exists
        assert soup.find(id='notifBtn') is not None, f"notifBtn not found on {page} page"
        assert soup.find(id='notifBadge') is not None, f"notifBadge not found on {page} page"
        assert soup.find(id='notifPopup') is not None, f"notifPopup not found on {page} page"
        assert soup.find(id='notifList') is not None, f"notifList not found on {page} page"
        assert soup.find(id='markAllReadBtn') is not None, f"markAllReadBtn not found on {page} page"
        
        # Verify JavaScript is present
        assert 'fetchNotifications' in html, f"fetchNotifications not found on {page} page"
        assert 'handleNotifClick' in html, f"handleNotifClick not found on {page} page"
    
    @given(
        notification_count=st.integers(min_value=1, max_value=5)
    )
    @settings(
        max_examples=10, 
        phases=[Phase.generate, Phase.target],
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_api_endpoints_return_correct_data(self, client, notification_count):
        """
        Property: API endpoints return correct notification data for any number of notifications.
        
        For any number of notifications (1-5), the /notifications/unread endpoint
        should return the correct count and notification items.
        
        **Validates: Requirements 3.5**
        """
        self.login_admin(client)
        
        # Clean up any existing notifications from previous test runs
        with app.app_context():
            admin = User.query.filter_by(username='adminuser').first()
            Notification.query.filter_by(user_id=admin.id).delete()
            db.session.commit()
        
        # Create notifications
        with app.app_context():
            admin = User.query.filter_by(username='adminuser').first()
            for i in range(notification_count):
                notif = Notification(
                    user_id=admin.id,
                    title=f'Property Test {i+1}',
                    message=f'Message {i+1}',
                    is_read=False
                )
                db.session.add(notif)
            db.session.commit()
        
        # Call API endpoint
        response = client.get('/notifications/unread')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['count'] == notification_count, \
            f"Expected count={notification_count}, got {data['count']}"
        assert len(data['items']) == notification_count, \
            f"Expected {notification_count} items, got {len(data['items'])}"
        
        # Verify each notification has required fields
        for item in data['items']:
            assert 'id' in item, "Notification item should have 'id' field"
            assert 'title' in item, "Notification item should have 'title' field"
            assert 'message' in item, "Notification item should have 'message' field"
            assert 'created_at_iso' in item, "Notification item should have 'created_at_iso' field"
    
    @given(
        mark_read_count=st.integers(min_value=1, max_value=5)
    )
    @settings(
        max_examples=10, 
        phases=[Phase.generate, Phase.target],
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_mark_read_updates_correctly(self, client, mark_read_count):
        """
        Property: Marking notifications as read updates the database correctly.
        
        For any number of notifications to mark as read (1-5), the mark-read
        endpoint should correctly update the is_read flag.
        
        **Validates: Requirements 3.5**
        """
        self.login_admin(client)
        
        # Clean up any existing notifications from previous test runs
        with app.app_context():
            admin = User.query.filter_by(username='adminuser').first()
            Notification.query.filter_by(user_id=admin.id).delete()
            db.session.commit()
        
        # Create notifications
        notif_ids = []
        with app.app_context():
            admin = User.query.filter_by(username='adminuser').first()
            for i in range(mark_read_count):
                notif = Notification(
                    user_id=admin.id,
                    title=f'Mark Read Test {i+1}',
                    message=f'Message {i+1}',
                    is_read=False
                )
                db.session.add(notif)
                db.session.flush()
                notif_ids.append(notif.id)
            db.session.commit()
        
        # Mark each notification as read
        for notif_id in notif_ids:
            response = client.post(f'/notifications/mark-read/{notif_id}')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data.get('success') is True
        
        # Verify all are marked as read
        with app.app_context():
            for notif_id in notif_ids:
                notif = Notification.query.get(notif_id)
                assert notif.is_read is True, f"Notification {notif_id} should be marked as read"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
