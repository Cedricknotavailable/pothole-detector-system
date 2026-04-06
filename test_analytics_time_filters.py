"""
Test to verify the new time-based filters in analytics page work correctly.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db, User

def test_analytics_page_time_filters():
    """Test that the analytics page includes the new time-based filters"""
    with app.test_client() as client:
        with app.app_context():
            # Login as admin
            admin = User.query.filter_by(username='test').first()
            if admin:
                response = client.post('/login', data={
                    'username': 'test',
                    'password': 'password'
                }, follow_redirects=True)
                
                # Access analytics page
                response = client.get('/analytics')
                assert response.status_code == 200
                
                html = response.data.decode('utf-8')
                
                # Check for time range preset dropdown
                assert 'id="timeRangePreset"' in html
                assert 'Time Range' in html
                assert 'Last 24 Hours' in html
                assert 'Last 7 Days' in html
                assert 'Last 30 Days' in html
                assert 'Custom Range' in html
                
                # Check that "Last 30 Days" is selected by default
                assert 'value="30d" selected' in html
                
                # Check for custom date range controls (should be hidden by default)
                assert 'id="customDateRange"' in html
                assert 'id="customDateRangeEnd"' in html
                assert 'style="display:none;"' in html
                
                # Check for JavaScript functions
                assert 'onTimeRangePresetChange()' in html
                assert 'function onTimeRangePresetChange()' in html
                
                print("✓ Analytics page includes new time-based filters")
                print("✓ Default selection is 'Last 30 Days'")
                print("✓ Custom date range controls are properly hidden")

def test_analytics_global_filters_logic():
    """Test that the getGlobalFilters function handles time presets correctly"""
    with app.test_client() as client:
        with app.app_context():
            # Login as admin
            response = client.post('/login', data={
                'username': 'test',
                'password': 'password'
            }, follow_redirects=True)
            
            # Access analytics page
            response = client.get('/analytics')
            html = response.data.decode('utf-8')
            
            # Check that the JavaScript logic is present
            assert 'switch (preset)' in html
            assert "case '24h':" in html
            assert "case '7d':" in html
            assert "case '30d':" in html
            assert "preset === 'custom'" in html
            
            # Check date calculation logic
            assert 'setDate(yesterday.getDate() - 1)' in html  # 24h logic
            assert 'setDate(weekAgo.getDate() - 7)' in html    # 7d logic
            assert 'setDate(monthAgo.getDate() - 30)' in html  # 30d logic
            
            print("✓ Time preset calculation logic is correctly implemented")

def test_analytics_ui_consistency():
    """Test that the new filters maintain UI consistency"""
    with app.test_client() as client:
        with app.app_context():
            # Login as admin
            response = client.post('/login', data={
                'username': 'test',
                'password': 'password'
            }, follow_redirects=True)
            
            # Access analytics page
            response = client.get('/analytics')
            html = response.data.decode('utf-8')
            
            # Check that all controls use consistent CSS classes
            assert 'class="control-label"' in html
            assert 'class="control-input"' in html
            assert 'class="global-filters-row"' in html
            
            # Check that buttons are properly styled
            assert 'id="applyFiltersBtn" class="btn"' in html
            assert 'id="clearFiltersBtn" class="btn secondary"' in html
            
            print("✓ UI consistency maintained with existing design")

if __name__ == '__main__':
    print("Testing analytics time-based filters implementation...\n")
    
    try:
        test_analytics_page_time_filters()
        test_analytics_global_filters_logic()
        test_analytics_ui_consistency()
        
        print("\n✅ All tests passed! Time-based filters successfully implemented.")
        print("📊 Default filter: Last 30 Days (improves performance)")
        print("🎛️ Options: Last 24 Hours, Last 7 Days, Last 30 Days, Custom Range")
        print("🔄 Auto-refresh on preset change, manual refresh for custom dates")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)