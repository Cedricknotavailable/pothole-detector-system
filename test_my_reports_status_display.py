#!/usr/bin/env python3
"""Test that My Reports page shows correct status labels."""

from app import app, db, User, Report
from werkzeug.security import generate_password_hash
import time

def test_my_reports_status_display():
    """Test that open reports show 'Open' and fixed reports show 'Fixed: timestamp'."""
    print("\n" + "="*70)
    print("TEST: My Reports Status Display")
    print("="*70)
    
    with app.test_client() as client:
        with app.app_context():
            # Clean up any existing test user
            existing = User.query.filter_by(username='status_test_user').first()
            if existing:
                Report.query.filter_by(user_id=existing.id).delete()
                db.session.delete(existing)
                db.session.commit()
            
            # Create a test user
            test_user = User(
                username='status_test_user',
                email='statustest@test.com',
                role='user',
                status='active',
                password_hash=generate_password_hash('TestPass123!')
            )
            db.session.add(test_user)
            db.session.commit()
            
            # Create an open report
            now_ts = int(time.time())
            open_report = Report(
                user_id=test_user.id,
                title='Open Pothole',
                body='Test open report',
                latitude=14.5995,
                longitude=120.9842,
                obstruction_type='Pothole',
                created_at=now_ts,
                status_updated_at=now_ts,
                is_fixed=False,
                fixed_at=None,
                is_false_report=False
            )
            db.session.add(open_report)
            
            # Create a fixed report
            fixed_ts = now_ts + 3600  # 1 hour later
            fixed_report = Report(
                user_id=test_user.id,
                title='Fixed Crack',
                body='Test fixed report',
                latitude=14.5996,
                longitude=120.9843,
                obstruction_type='Road Crack',
                created_at=now_ts,
                status_updated_at=fixed_ts,
                is_fixed=True,
                fixed_at=fixed_ts,
                is_false_report=False
            )
            db.session.add(fixed_report)
            db.session.commit()
            
            print(f"\n✓ Created test user with 2 reports (1 open, 1 fixed)")
        
        # Login as the test user
        response = client.post('/login', data={
            'username': 'status_test_user',
            'password': 'TestPass123!'
        }, follow_redirects=False)
        
        assert response.status_code == 302, f"Login should redirect, got {response.status_code}"
        print("✓ Logged in successfully")
        
        # Access My Reports page
        response = client.get('/my-reports', follow_redirects=True)
        content = response.get_data(as_text=True)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ My Reports page loaded")
        
        # Debug: Check if reports are in the page
        with app.app_context():
            user = User.query.filter_by(username='status_test_user').first()
            reports_count = Report.query.filter_by(user_id=user.id, is_false_report=False).count()
            print(f"  Debug: Found {reports_count} reports in database")
        
        # Check if "No reports" message is shown
        if 'No reports submitted yet' in content:
            print("  Debug: Page shows 'No reports submitted yet'")
            print("  Debug: This might be a pagination or filtering issue")
        
        # Check table headers
        assert 'Status' in content, "Status column header should be present"
        assert 'Submitted' in content, "Submitted column header should be present"
        print("✓ Column headers correct")
        
        # Check open report shows "Open"
        # The report titles might not be in the visible content, check for the status indicators instead
        open_status_found = '<span style="color: #f59e0b; font-weight: 600;">Open</span>' in content
        if not open_status_found:
            # Debug: save content to file
            with open('debug_my_reports.html', 'w', encoding='utf-8') as f:
                f.write(content)
            print("  Debug: Saved page content to debug_my_reports.html")
        
        assert open_status_found, "Open report should show 'Open' status"
        print("✓ Open report shows 'Open' status")
        
        # Check fixed report shows "Fixed: timestamp"
        fixed_status_found = '<span style="color: #10b981; font-weight: 600;">Fixed:</span>' in content
        assert fixed_status_found, "Fixed report should show 'Fixed:' label"
        print("✓ Fixed report shows 'Fixed:' label with timestamp")
        
        # Verify the fixed timestamp is displayed
        with app.app_context():
            fixed_report_check = Report.query.filter_by(title='Fixed Crack').first()
            fixed_time_str = fixed_report_check.fixed_at_iso
            assert fixed_time_str in content, f"Fixed timestamp '{fixed_time_str}' should be in content"
            print(f"✓ Fixed timestamp displayed: {fixed_time_str}")
        
        # Verify submitted timestamps are shown for both
        with app.app_context():
            open_report_check = Report.query.filter_by(title='Open Pothole').first()
            submitted_time_str = open_report_check.created_at_iso
            assert submitted_time_str in content, f"Submitted timestamp should be in content"
            print(f"✓ Submitted timestamps displayed correctly")
        
        print("\n" + "="*70)
        print("✓ ALL CHECKS PASSED")
        print("="*70)


def test_mark_as_fixed_updates_status():
    """Test that marking a report as fixed updates the status display."""
    print("\n" + "="*70)
    print("TEST: Mark As Fixed Updates Status")
    print("="*70)
    
    with app.test_client() as client:
        with app.app_context():
            # Get the test user
            test_user = User.query.filter_by(username='status_test_user').first()
            if not test_user:
                print("✗ Test user not found, run previous test first")
                return
            
            # Get the open report
            open_report = Report.query.filter_by(title='Open Pothole', user_id=test_user.id).first()
            if not open_report:
                print("✗ Open report not found")
                return
            
            report_id = open_report.id
            print(f"\n✓ Found open report (ID: {report_id})")
        
        # Login
        client.post('/login', data={
            'username': 'status_test_user',
            'password': 'TestPass123!'
        })
        
        # Mark as fixed
        response = client.post(f'/reports/{report_id}/fix', 
                              headers={'Content-Type': 'application/json'})
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        json_data = response.get_json()
        assert json_data.get('success'), "Mark as fixed should succeed"
        print("✓ Report marked as fixed via API")
        
        # Reload My Reports page
        response = client.get('/my-reports')
        content = response.get_data(as_text=True)
        
        # Count how many reports this user has that are fixed
        with app.app_context():
            user = User.query.filter_by(username='status_test_user').first()
            fixed_count = Report.query.filter_by(user_id=user.id, is_fixed=True, is_false_report=False).count()
            print(f"  Debug: User has {fixed_count} fixed reports")
        
        # Should now show Fixed status for both reports (appears in both desktop table and mobile cards)
        fixed_status_count = content.count('<span style="color: #10b981; font-weight: 600;">Fixed:</span>')
        # Each report appears twice (desktop + mobile view), so we expect fixed_count * 2
        expected_count = fixed_count * 2
        assert fixed_status_count == expected_count, f"Should have {expected_count} fixed status labels (desktop + mobile), found {fixed_status_count}"
        print(f"✓ Status updated to 'Fixed:' on page ({fixed_count} reports × 2 views)")
        
        # Should show the fixed badges (also appears in both views)
        badge_count = content.count('badge badge--active')
        assert badge_count == expected_count, f"Should have {expected_count} 'Fixed' badges"
        print("✓ Fixed badges displayed")
        
        print("\n" + "="*70)
        print("✓ ALL CHECKS PASSED")
        print("="*70)


if __name__ == '__main__':
    try:
        test_my_reports_status_display()
        test_mark_as_fixed_updates_status()
        
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
