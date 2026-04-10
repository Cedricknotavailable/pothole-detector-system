#!/usr/bin/env python3
"""
Test script for moderator false report flagging implementation.
Verifies that moderators can flag reports as false and users receive proper notifications.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Report, Notification, Settings
import json

def test_moderator_false_report_flagging():
    """Test that moderators can flag reports as false with proper notifications"""
    
    with app.app_context():
        # Clean up any existing test data
        db.session.query(Notification).filter(Notification.title == "Report Flagged as False").delete()
        db.session.query(Report).filter(Report.title.like("Test Report%")).delete()
        db.session.query(User).filter(User.username.like("test_%")).delete()
        db.session.commit()
        
        # Create test users
        regular_user = User(
            username='test_regular_user',
            email='regular@test.com',
            password_hash='dummy_hash',
            role='user',
            status='active',
            false_reports_count=0
        )
        
        moderator_user = User(
            username='test_moderator',
            email='moderator@test.com', 
            password_hash='dummy_hash',
            role='moderator',
            status='active'
        )
        
        db.session.add(regular_user)
        db.session.add(moderator_user)
        db.session.commit()
        
        # Create test report
        test_report = Report(
            user_id=regular_user.id,
            title='Test Report for False Flagging',
            body='This is a test report',
            latitude=40.7128,
            longitude=-74.0060,
            is_false_report=False
        )
        
        db.session.add(test_report)
        db.session.commit()
        
        # Ensure false report threshold setting exists
        threshold_setting = Settings.query.filter_by(key='false_report_threshold').first()
        if not threshold_setting:
            threshold_setting = Settings(key='false_report_threshold', value='5')
            db.session.add(threshold_setting)
            db.session.commit()
        
        print("=== Testing Moderator False Report Flagging ===")
        
        # Test 1: Moderator can access the endpoint
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = moderator_user.id
            
            response = client.post(f'/reports/{test_report.id}/flag-false')
            print(f"✓ Moderator access test: {response.status_code == 200}")
            
            if response.status_code == 200:
                data = json.loads(response.data)
                print(f"✓ Response success: {data.get('success', False)}")
            
        # Test 2: Verify report is marked as false
        db.session.refresh(test_report)
        print(f"✓ Report marked as false: {test_report.is_false_report}")
        
        # Test 3: Verify user's false report count incremented
        db.session.refresh(regular_user)
        print(f"✓ User false report count incremented: {regular_user.false_reports_count == 1}")
        
        # Test 4: Verify notification was created with proper message
        notification = Notification.query.filter_by(
            user_id=regular_user.id,
            title="Report Flagged as False"
        ).first()
        
        print(f"✓ Notification created: {notification is not None}")
        
        if notification:
            expected_parts = [
                "Test Report for False Flagging",
                "flagged as a false report",
                "submitted 1 false report",
                "4 more false report(s) will result in account suspension"
            ]
            
            message_correct = all(part in notification.message for part in expected_parts)
            print(f"✓ Notification message correct: {message_correct}")
            
            if not message_correct:
                print(f"   Actual message: {notification.message}")
        
        # Test 5: Test account locking scenario
        print("\n=== Testing Account Locking Scenario ===")
        
        # Set user to 4 false reports (one away from threshold)
        regular_user.false_reports_count = 4
        db.session.commit()
        
        # Create another test report
        test_report2 = Report(
            user_id=regular_user.id,
            title='Test Report 2 for Locking',
            body='This will trigger account lock',
            latitude=40.7128,
            longitude=-74.0060,
            is_false_report=False
        )
        
        db.session.add(test_report2)
        db.session.commit()
        
        # Flag this report (should trigger account lock)
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = moderator_user.id
            
            response = client.post(f'/reports/{test_report2.id}/flag-false')
            print(f"✓ Second flag request successful: {response.status_code == 200}")
        
        # Verify account is locked
        db.session.refresh(regular_user)
        print(f"✓ User account locked: {regular_user.status == 'locked'}")
        print(f"✓ Final false report count: {regular_user.false_reports_count == 5}")
        
        # Verify lock notification message
        lock_notification = Notification.query.filter_by(
            user_id=regular_user.id,
            title="Report Flagged as False"
        ).order_by(Notification.id.desc()).first()
        
        if lock_notification:
            lock_message_correct = (
                "account has been locked" in lock_notification.message and
                "submitting 5 false reports" in lock_notification.message
            )
            print(f"✓ Lock notification message correct: {lock_message_correct}")
            
            if not lock_message_correct:
                print(f"   Actual lock message: {lock_notification.message}")
        
        # Test 6: Verify admin users can still access (backward compatibility)
        print("\n=== Testing Admin Access (Backward Compatibility) ===")
        
        admin_user = User(
            username='test_admin',
            email='admin@test.com',
            password_hash='dummy_hash', 
            role='admin',
            status='active'
        )
        
        db.session.add(admin_user)
        db.session.commit()
        
        # Create another test report
        test_report3 = Report(
            user_id=regular_user.id,
            title='Test Report 3 for Admin',
            body='Admin test',
            latitude=40.7128,
            longitude=-74.0060,
            is_false_report=False
        )
        
        db.session.add(test_report3)
        db.session.commit()
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = admin_user.id
            
            response = client.post(f'/reports/{test_report3.id}/flag-false')
            print(f"✓ Admin access still works: {response.status_code == 200}")
        
        # Clean up test data
        print("\n=== Cleaning Up Test Data ===")
        db.session.query(Notification).filter(Notification.title == "Report Flagged as False").delete()
        db.session.query(Report).filter(Report.title.like("Test Report%")).delete()
        db.session.query(User).filter(User.username.like("test_%")).delete()
        db.session.commit()
        print("✓ Test data cleaned up")

if __name__ == '__main__':
    test_moderator_false_report_flagging()
    print("\n=== Test Complete ===")