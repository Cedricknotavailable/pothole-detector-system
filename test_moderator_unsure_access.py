"""
Test to verify moderators have access to unsure detection filters and review functionality.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db, User, Detection
import time

def test_moderator_unsure_filter_access():
    """Test that moderators can access the unsure filter in defects page"""
    with app.test_client() as client:
        with app.app_context():
            # Create a moderator user
            moderator = User.query.filter_by(username='testmoderator').first()
            if not moderator:
                moderator = User(
                    username='testmoderator',
                    email='moderator@test.com',
                    role='moderator',
                    status='active'
                )
                moderator.set_password('password123')
                db.session.add(moderator)
                db.session.commit()
            
            # Login as moderator
            response = client.post('/login', data={
                'username': 'testmoderator',
                'password': 'password123'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Access defects page
            response = client.get('/defects')
            assert response.status_code == 200
            
            # Check that the unsure filter option is present in the response
            html = response.data.decode('utf-8')
            assert 'value="unsure"' in html, "Unsure filter option should be available for moderators"
            assert 'Unsure (AI)' in html, "Unsure filter label should be present"
            
            print("✓ Moderator can access unsure filter in defects page")

def test_moderator_map_unsure_access():
    """Test that moderators can access the unsure filter in map page"""
    with app.test_client() as client:
        with app.app_context():
            # Login as moderator
            response = client.post('/login', data={
                'username': 'testmoderator',
                'password': 'password123'
            }, follow_redirects=True)
            
            # Access map page
            response = client.get('/map')
            assert response.status_code == 200
            
            # Check that IS_ADMIN_OR_MODERATOR is set to true
            html = response.data.decode('utf-8')
            assert 'IS_ADMIN_OR_MODERATOR = true' in html, "IS_ADMIN_OR_MODERATOR should be true for moderators"
            assert 'data-type="unsure"' in html, "Unsure filter button should be present"
            
            print("✓ Moderator can access unsure filter in map page")

def test_moderator_detection_review():
    """Test that moderators can review detections"""
    with app.test_client() as client:
        with app.app_context():
            # Create a pending detection
            detection = Detection(
                latitude=14.5995,
                longitude=120.9842,
                label='pothole',
                detected_class='pothole',
                confidence=0.45,
                review_status='pending',
                visibility_scope='admin_only',
                created_at=int(time.time()),
                status_updated_at=int(time.time())
            )
            db.session.add(detection)
            db.session.commit()
            detection_id = detection.id
            
            # Login as moderator
            client.post('/login', data={
                'username': 'testmoderator',
                'password': 'password123'
            }, follow_redirects=True)
            
            # Try to review the detection
            response = client.post(f'/detections/{detection_id}/review', 
                json={'action': 'confirm_pothole'},
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] == True, "Moderator should be able to review detections"
            
            # Verify the detection was updated
            updated_detection = Detection.query.get(detection_id)
            assert updated_detection.review_status == 'confirmed'
            assert updated_detection.visibility_scope == 'public'
            
            print("✓ Moderator can review detections")
            
            # Cleanup
            db.session.delete(updated_detection)
            db.session.commit()

def test_moderator_pending_detections_access():
    """Test that moderators can fetch pending detections"""
    with app.test_client() as client:
        with app.app_context():
            # Login as moderator
            client.post('/login', data={
                'username': 'testmoderator',
                'password': 'password123'
            }, follow_redirects=True)
            
            # Fetch detections with include_pending flag
            response = client.get('/detections?include_pending=1')
            assert response.status_code == 200
            
            data = response.get_json()
            assert 'items' in data, "Response should contain items"
            
            print("✓ Moderator can fetch pending detections")

if __name__ == '__main__':
    print("Testing moderator access to unsure detection filters...\n")
    
    try:
        test_moderator_unsure_filter_access()
        test_moderator_map_unsure_access()
        test_moderator_detection_review()
        test_moderator_pending_detections_access()
        
        print("\n✅ All tests passed! Moderators now have access to unsure detection filters and review functionality.")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
