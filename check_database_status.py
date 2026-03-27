"""
Script to check database status and compare with backup
"""
import sqlite3
import os
from datetime import datetime

def check_database(db_path, label):
    """Check database contents"""
    print(f"\n{'='*60}")
    print(f"{label}: {db_path}")
    print(f"{'='*60}")
    
    if not os.path.exists(db_path):
        print(f"❌ Database file does not exist!")
        return None
    
    file_size = os.path.getsize(db_path)
    mod_time = datetime.fromtimestamp(os.path.getmtime(db_path))
    print(f"File size: {file_size:,} bytes")
    print(f"Last modified: {mod_time}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check users
        cursor.execute("SELECT COUNT(*) FROM user")
        user_count = cursor.fetchone()[0]
        print(f"\n👥 Users: {user_count}")
        
        cursor.execute("SELECT id, username, email, role, status FROM user ORDER BY id")
        users = cursor.fetchall()
        for user in users:
            print(f"  - ID {user[0]}: {user[1]} ({user[2]}) - Role: {user[3]}, Status: {user[4]}")
        
        # Check reports
        cursor.execute("SELECT COUNT(*) FROM report")
        report_count = cursor.fetchone()[0]
        print(f"\n📝 Reports: {report_count}")
        
        cursor.execute("SELECT COUNT(*) FROM report WHERE is_fixed = 0")
        open_reports = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM report WHERE is_fixed = 1")
        fixed_reports = cursor.fetchone()[0]
        print(f"  - Open: {open_reports}")
        print(f"  - Fixed: {fixed_reports}")
        
        # Check detections
        cursor.execute("SELECT COUNT(*) FROM detection")
        detection_count = cursor.fetchone()[0]
        print(f"\n🔍 Detections: {detection_count}")
        
        cursor.execute("SELECT COUNT(*) FROM detection WHERE is_fixed = 0")
        open_detections = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM detection WHERE is_fixed = 1")
        fixed_detections = cursor.fetchone()[0]
        print(f"  - Open: {open_detections}")
        print(f"  - Fixed: {fixed_detections}")
        
        conn.close()
        
        return {
            'users': user_count,
            'reports': report_count,
            'detections': detection_count,
            'file_size': file_size
        }
        
    except Exception as e:
        print(f"❌ Error reading database: {e}")
        return None

# Check current database
current_db = 'instance/users.db'
current_stats = check_database(current_db, "CURRENT DATABASE")

# Check backup
backup_db = 'backups/backup_20260312_110631.db'
if os.path.exists(backup_db):
    backup_stats = check_database(backup_db, "BACKUP DATABASE (March 12, 2026)")
    
    if current_stats and backup_stats:
        print(f"\n{'='*60}")
        print("COMPARISON")
        print(f"{'='*60}")
        print(f"Users: Current={current_stats['users']}, Backup={backup_stats['users']}, Diff={current_stats['users'] - backup_stats['users']}")
        print(f"Reports: Current={current_stats['reports']}, Backup={backup_stats['reports']}, Diff={current_stats['reports'] - backup_stats['reports']}")
        print(f"Detections: Current={current_stats['detections']}, Backup={backup_stats['detections']}, Diff={current_stats['detections'] - backup_stats['detections']}")
        
        if (current_stats['users'] < backup_stats['users'] or 
            current_stats['reports'] < backup_stats['reports'] or 
            current_stats['detections'] < backup_stats['detections']):
            print("\n⚠️  WARNING: Current database has LESS data than backup!")
            print("   Data loss may have occurred.")
        elif (current_stats['users'] == backup_stats['users'] and 
              current_stats['reports'] == backup_stats['reports'] and 
              current_stats['detections'] == backup_stats['detections']):
            print("\n✅ Database matches backup (no new data added)")
        else:
            print("\n✅ Database has more data than backup (expected if new data was added)")
else:
    print(f"\n⚠️  Backup file not found: {backup_db}")

print(f"\n{'='*60}\n")
