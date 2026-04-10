#!/usr/bin/env python3
"""
Find reports that can be used for testing admin flagging
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Report

def find_test_reports():
    """Find reports that can be used for testing"""
    
    with app.app_context():
        print("=== Finding Test Reports ===")
        
        users = User.query.filter(User.role == 'user').all()
        for user in users:
            reports = Report.query.filter_by(user_id=user.id, is_false_report=False).all()
            if reports:
                print(f'User {user.username}: {len(reports)} unflagged reports')
                for r in reports[:2]:
                    print(f'  Report {r.id}: {r.title}')
                print()

if __name__ == '__main__':
    find_test_reports()