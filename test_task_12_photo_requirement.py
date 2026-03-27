"""
Test suite for Task 12: Required Photo Attachment

This test suite validates:
- Task 12.1: HTML form updates (required attribute, label changes, error div)
- Task 12.2: Client-side validation (file presence, type, size)
- Task 12.3: Server-side validation (file presence, type, size, error messages)

Requirements validated: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

import pytest
import os
import io
from app import app, db, User, Report
from werkzeug.security import generate_password_hash


@pytest.fixture(scope='function')
def client():
    """Create test client with in-memory database"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            db.drop_all()  # Ensure clean state
            db.create_all()
            # Create test user
            user = User(
                username='testuser',
                email='test@example.com',
                role='user',
                status='active'
            )
            user.password_hash = generate_password_hash('password123')
            db.session.add(user)
            db.session.commit()
        yield client
        # Cleanup
        with app.app_context():
            db.session.remove()
            db.drop_all()


@pytest.fixture(scope='function')
def auth_client(client):
    """Authenticated test client"""
    with client.session_transaction() as sess:
        # Get user ID
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            sess['user_id'] = user.id
            sess['csrf_token'] = 'test-token'
    return client


def create_test_image(size_mb=1):
    """Create a test image file in memory"""
    # Create a simple PNG file (1x1 pixel)
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    
    # Pad to desired size
    if size_mb > 0:
        padding_size = int(size_mb * 1024 * 1024) - len(png_data)
        if padding_size > 0:
            png_data += b'\x00' * padding_size
    
    return io.BytesIO(png_data)


class TestTask12_1_HTMLUpdates:
    """Test Task 12.1: Update report form HTML"""
    
    def test_photo_input_has_required_attribute(self, auth_client):
        """Verify photo input has required attribute"""
        response = auth_client.get('/reports')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        
        # Check for required attribute on photo input
        assert 'id="photo"' in html
        assert 'type="file"' in html
        assert 'required' in html
        
    def test_label_changed_from_optional_to_required(self, auth_client):
        """Verify label changed from 'Evidence Photo (Optional)' to 'Evidence Photo'"""
        response = auth_client.get('/reports')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        
        # Should NOT contain "(Optional)"
        assert 'Evidence Photo (Optional)' not in html
        
        # Should contain just "Evidence Photo"
        assert 'Evidence Photo</label>' in html or 'Evidence Photo"' in html
        
    def test_photo_error_div_exists(self, auth_client):
        """Verify photo error message div exists"""
        response = auth_client.get('/reports')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        
        # Check for error div
        assert 'id="photoError"' in html
        assert 'Photo is required' in html
        
    def test_placeholder_text_indicates_required(self, auth_client):
        """Verify upload placeholder text indicates required"""
        response = auth_client.get('/reports')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        
        # Check for "required" in placeholder text
        assert 'upload photo (required)' in html.lower() or 'required' in html


class TestTask12_2_ClientSideValidation:
    """Test Task 12.2: Client-side photo validation (via HTML attributes)"""
    
    def test_form_has_photo_validation_script(self, auth_client):
        """Verify form has client-side validation JavaScript"""
        response = auth_client.get('/reports')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        
        # Check for photo validation logic in JavaScript
        assert 'photoInput' in html or 'photo' in html
        assert 'files' in html
        
    def test_error_clearing_on_file_selection(self, auth_client):
        """Verify error clearing logic exists for photo input"""
        response = auth_client.get('/reports')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        
        # Check for event listener on photo input
        assert 'addEventListener' in html
        assert 'photoError' in html


class TestTask12_3_ServerSideValidation:
    """Test Task 12.3: Server-side photo validation"""
    
    def test_submission_without_photo_rejected(self, auth_client):
        """Verify submission without photo is rejected with error message"""
        response = auth_client.post('/reports', data={
            'csrf_token': 'test-token',
            'latitude': '14.5',
            'longitude': '121.0',
            'obstruction_type': 'Pothole'
            # No photo file
        }, follow_redirects=False)
        
        assert response.status_code == 200  # Returns to form with errors
        html = response.data.decode('utf-8')
        assert 'Photo is required' in html
        
        # Verify no report was created
        with app.app_context():
            report_count = Report.query.count()
            assert report_count == 0
    
    def test_submission_with_valid_photo_succeeds(self, auth_client):
        """Verify submission with valid photo succeeds"""
        photo = create_test_image(size_mb=1)
        
        response = auth_client.post('/reports', data={
            'csrf_token': 'test-token',
            'latitude': '14.5',
            'longitude': '121.0',
            'obstruction_type': 'Pothole',
            'photo': (photo, 'test.png')
        }, content_type='multipart/form-data', follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify report was created
        with app.app_context():
            report = Report.query.first()
            assert report is not None
            assert report.photo_path is not None
            assert 'uploads/reports/' in report.photo_path
    
    def test_invalid_file_type_rejected(self, auth_client):
        """Verify invalid file types (non-JPG/PNG) are rejected"""
        # Create a fake text file
        fake_file = io.BytesIO(b'This is not an image')
        
        response = auth_client.post('/reports', data={
            'csrf_token': 'test-token',
            'latitude': '14.5',
            'longitude': '121.0',
            'obstruction_type': 'Pothole',
            'photo': (fake_file, 'test.txt')
        }, content_type='multipart/form-data', follow_redirects=False)
        
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert 'Photo must be a .jpg, .jpeg, or .png' in html or 'Invalid' in html
        
        # Verify no report was created
        with app.app_context():
            report_count = Report.query.count()
            assert report_count == 0
    
    def test_file_size_validation_max_5mb(self, auth_client):
        """Verify files larger than 5MB are rejected"""
        # Create a 6MB file
        large_photo = create_test_image(size_mb=6)
        
        response = auth_client.post('/reports', data={
            'csrf_token': 'test-token',
            'latitude': '14.5',
            'longitude': '121.0',
            'obstruction_type': 'Pothole',
            'photo': (large_photo, 'large.png')
        }, content_type='multipart/form-data', follow_redirects=False)
        
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert 'too large' in html.lower() or '5MB' in html or '5 MB' in html
        
        # Verify no report was created
        with app.app_context():
            report_count = Report.query.count()
            assert report_count == 0
    
    def test_jpg_file_accepted(self, auth_client):
        """Verify JPG files are accepted"""
        photo = create_test_image(size_mb=1)
        
        response = auth_client.post('/reports', data={
            'csrf_token': 'test-token',
            'latitude': '14.5',
            'longitude': '121.0',
            'obstruction_type': 'Pothole',
            'photo': (photo, 'test.jpg')
        }, content_type='multipart/form-data', follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify report was created
        with app.app_context():
            report = Report.query.first()
            assert report is not None
            assert report.photo_path.endswith('.jpg')
    
    def test_jpeg_file_accepted(self, auth_client):
        """Verify JPEG files are accepted"""
        photo = create_test_image(size_mb=1)
        
        response = auth_client.post('/reports', data={
            'csrf_token': 'test-token',
            'latitude': '14.5',
            'longitude': '121.0',
            'obstruction_type': 'Pothole',
            'photo': (photo, 'test.jpeg')
        }, content_type='multipart/form-data', follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify report was created
        with app.app_context():
            report = Report.query.first()
            assert report is not None
            assert report.photo_path.endswith('.jpeg')
    
    def test_specific_error_messages_returned(self, auth_client):
        """Verify specific error messages are returned for different validation failures"""
        # Test 1: Missing photo
        response = auth_client.post('/reports', data={
            'csrf_token': 'test-token',
            'latitude': '14.5',
            'longitude': '121.0',
            'obstruction_type': 'Pothole'
        }, follow_redirects=False)
        
        html = response.data.decode('utf-8')
        assert 'Photo is required' in html
        
        # Test 2: Invalid file type
        fake_file = io.BytesIO(b'fake')
        response = auth_client.post('/reports', data={
            'csrf_token': 'test-token',
            'latitude': '14.5',
            'longitude': '121.0',
            'obstruction_type': 'Pothole',
            'photo': (fake_file, 'test.pdf')
        }, content_type='multipart/form-data', follow_redirects=False)
        
        html = response.data.decode('utf-8')
        assert '.jpg' in html or '.png' in html or 'image' in html.lower()
    
    def test_report_not_created_if_photo_missing(self, auth_client):
        """Verify report creation is prevented if photo is missing"""
        initial_count = 0
        with app.app_context():
            initial_count = Report.query.count()
        
        response = auth_client.post('/reports', data={
            'csrf_token': 'test-token',
            'latitude': '14.5',
            'longitude': '121.0',
            'obstruction_type': 'Pothole'
        }, follow_redirects=False)
        
        with app.app_context():
            final_count = Report.query.count()
            assert final_count == initial_count  # No new report created


class TestTask12_Integration:
    """Integration tests for complete photo requirement workflow"""
    
    def test_complete_submission_workflow(self, auth_client):
        """Test complete report submission with photo"""
        photo = create_test_image(size_mb=2)
        
        response = auth_client.post('/reports', data={
            'csrf_token': 'test-token',
            'latitude': '14.5995',
            'longitude': '120.9842',
            'obstruction_type': 'Road Crack',
            'photo': (photo, 'roadcrack.png')
        }, content_type='multipart/form-data', follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify report was created with all correct data
        with app.app_context():
            report = Report.query.first()
            assert report is not None
            assert report.latitude == 14.5995
            assert report.longitude == 120.9842
            assert report.obstruction_type == 'Road Crack'
            assert report.photo_path is not None
            assert 'uploads/reports/' in report.photo_path
            assert report.photo_path.endswith('.png')
    
    def test_form_preserves_values_on_photo_error(self, auth_client):
        """Verify form preserves other field values when photo validation fails"""
        response = auth_client.post('/reports', data={
            'csrf_token': 'test-token',
            'latitude': '14.5',
            'longitude': '121.0',
            'obstruction_type': 'Pothole'
            # Missing photo
        }, follow_redirects=False)
        
        html = response.data.decode('utf-8')
        
        # Check that values are preserved
        assert '14.5' in html
        assert '121.0' in html
        assert 'Pothole' in html


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
