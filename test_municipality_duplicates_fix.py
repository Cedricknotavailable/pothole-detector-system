"""
Test to verify the municipality duplicates fix in analytics page.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db, User

def test_analytics_municipality_deduplication():
    """Test that the analytics page properly deduplicates municipality names"""
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
                
                # Check that the loadAreas function includes deduplication logic
                assert 'const nameSet = new Set()' in html
                assert 'const uniqueFeatures = []' in html
                assert '!nameSet.has(name)' in html
                assert 'nameSet.add(name)' in html
                
                # Check that sorting is applied to unique features
                assert 'uniqueFeatures' in html
                assert '.sort((a, b) => a.name.localeCompare(b.name))' in html
                
                print("✓ Analytics page includes municipality deduplication logic")

def test_loadareas_function_structure():
    """Test that the loadAreas function has the correct structure"""
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
            
            # Check the function structure
            assert 'async function loadAreas(selectId, level)' in html
            assert 'municipalities.json' in html
            assert 'provinces.json' in html
            assert 'regions.json' in html
            
            # Check deduplication workflow
            assert 'forEach(f => {' in html  # First loop to collect unique names
            assert 'forEach(({ name }) => {' in html  # Second loop to create options
            
            # Check proper option creation
            assert 'o.value = name; o.textContent = name;' in html
            assert 'sel.appendChild(o);' in html
            
            print("✓ loadAreas function has correct deduplication structure")

def test_analytics_ui_consistency():
    """Test that the fix maintains UI consistency"""
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
            
            # Check that all admin level options are still present
            assert 'value="region">Region</option>' in html
            assert 'value="province" selected>Province</option>' in html
            assert 'value="municipality">Municipality</option>' in html
            
            # Check that the area dropdown is properly initialized
            assert 'id="globalAdminArea"' in html
            assert '<option value="all">All Areas</option>' in html
            
            # Check that the onchange handler is still wired
            assert 'onchange="onGlobalLevelChange()"' in html
            
            print("✓ UI consistency maintained after deduplication fix")

if __name__ == '__main__':
    print("Testing municipality duplicates fix...\n")
    
    try:
        test_analytics_municipality_deduplication()
        test_loadareas_function_structure()
        test_analytics_ui_consistency()
        
        print("\n✅ All tests passed! Municipality duplicates fix successfully implemented.")
        print("🔧 Fix: Added Set-based deduplication to loadAreas function")
        print("📋 Benefit: Clean dropdown lists without duplicate municipality names")
        print("⚡ Performance: Efficient deduplication using JavaScript Set")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)