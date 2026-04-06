"""
Test to verify the Activity Logs page works correctly.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db, User

def test_activity_logs_page_access():
    """Test that admins and moderators can access the activity logs page"""
    with app.test_client() as client:
        with app.app_context():
            # Test admin access
            admin = User.query.filter_by(username='test').first()
            if admin:
                response = client.post('/login', data={
                    'username': 'test',
                    'password': 'password'
                }, follow_redirects=True)
                
                # Access activity logs page
                response = client.get('/activity-logs')
                assert response.status_code == 200
                
                html = response.data.decode('utf-8')
                assert 'Activity Logs' in html
                assert 'Chronological record of significant system actions' in html
                assert 'auditActionFilter' in html
                assert 'auditActorFilter' in html
                assert 'Export CSV' in html
                
                print("✓ Admin can access Activity Logs page")
            
            # Test moderator access
            moderator = User.query.filter_by(username='modAcc').first()
            if moderator:
                response = client.post('/login', data={
                    'username': 'modAcc',
                    'password': 'Password1!'
                }, follow_redirects=True)
                
                # Access activity logs page
                response = client.get('/activity-logs')
                assert response.status_code == 200
                
                html = response.data.decode('utf-8')
                assert 'Activity Logs' in html
                assert 'auditActionFilter' in html
                
                print("✓ Moderator can access Activity Logs page")

def test_analytics_page_no_audit_log():
    """Test that the analytics page no longer contains audit log section"""
    with app.test_client() as client:
        with app.app_context():
            # Login as admin
            response = client.post('/login', data={
                'username': 'test',
                'password': 'password'
            }, follow_redirects=True)
            
            # Access analytics page
            response = client.get('/analytics')
            assert response.status_code == 200
            
            html = response.data.decode('utf-8')
            assert 'Analytics Dashboard' in html
            assert 'Detection Trends' in html
            assert 'Geographic Heatmap' in html
            assert 'AI Confidence Distribution' in html
            
            # Verify audit log section is removed
            assert 'System Activity Log' not in html
            assert 'auditActionFilter' not in html
            assert 'auditActorFilter' not in html
            
            print("✓ Analytics page no longer contains audit log section")

def test_navigation_includes_activity_logs():
    """Test that navigation includes Activity Logs link"""
    with app.test_client() as client:
        with app.app_context():
            # Login as admin
            response = client.post('/login', data={
                'username': 'test',
                'password': 'password'
            }, follow_redirects=True)
            
            # Check analytics page navigation
            response = client.get('/analytics')
            html = response.data.decode('utf-8')
            assert 'href="/activity-logs"' in html
            assert 'Activity Logs' in html
            
            # Check activity logs page navigation
            response = client.get('/activity-logs')
            html = response.data.decode('utf-8')
            assert 'href="/analytics"' in html
            assert 'class="active" href="/activity-logs"' in html
            
            print("✓ Navigation properly includes Activity Logs link")

if __name__ == '__main__':
    print("Testing Activity Logs page implementation...\n")
    
    try:
        test_activity_logs_page_access()
        test_analytics_page_no_audit_log()
        test_navigation_includes_activity_logs()
        
        print("\n✅ All tests passed! Activity Logs page successfully implemented.")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)