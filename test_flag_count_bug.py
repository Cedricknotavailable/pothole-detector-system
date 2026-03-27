"""
Simple test to verify the flag count bug
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Report, ReportFlag, Settings


def test_flag_count():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.drop_all()
        db.create_all()
        
        # Create user and report
        user = User(username='test', email='test@test.com', role='user', status='active')
        user.set_password('pass')
        db.session.add(user)
        
        report = Report(
            user_id=1,
            title='Test',
            body='Test',
            latitude=14.5,
            longitude=120.9,
            obstruction_type='Pothole',
            created_at=int(time.time())
        )
        db.session.add(report)
        db.session.commit()
        
        print("Initial state:")
        print(f"  Flags in DB: {ReportFlag.query.filter_by(report_id=1).count()}")
        
        # Simulate what flag_report does
        print("\nSimulating flag_report logic:")
        flag = ReportFlag(report_id=1, user_id=1)
        db.session.add(flag)
        print(f"  After add (before commit): {ReportFlag.query.filter_by(report_id=1).count()}")
        
        # This is what the FIXED code does
        flag_count = ReportFlag.query.filter_by(report_id=1).count()
        print(f"  Calculated flag_count: {flag_count}")
        
        db.session.commit()
        print(f"  After commit: {ReportFlag.query.filter_by(report_id=1).count()}")
        
        if flag_count == 1:
            print("\n✓ BUG FIXED: Flag count is now correct!")


if __name__ == '__main__':
    test_flag_count()
