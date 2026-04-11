#!/usr/bin/env python3
"""Script to trigger backups via the API endpoint."""

import requests
import sys

# Configuration
BACKUP_API_KEY = "ae3784f4ecd2960e7fe3ad2a58a84469b257ee60f808f5188245080ad85e8508"
APP_BASE_URL = "http://172.24.156.42:8000"  # Change this to your deployed URL if needed

def trigger_backup(backup_type):
    """Trigger a backup via the API endpoint.
    
    Args:
        backup_type: Either "daily" or "monthly"
    """
    url = f"{APP_BASE_URL}/api/backups/scheduled"
    headers = {
        "X-Backup-Api-Key": BACKUP_API_KEY,
        "Content-Type": "application/json"
    }
    data = {"type": backup_type}
    
    print(f"Triggering {backup_type} backup...")
    print(f"URL: {url}")
    print()
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print(f"\n✓ {backup_type.capitalize()} backup triggered successfully!")
        else:
            print(f"\n✗ Failed to trigger backup")
            
    except requests.exceptions.ConnectionError:
        print("✗ CONNECTION ERROR")
        print(f"  Could not connect to Flask app at {APP_BASE_URL}")
        print(f"\n  Make sure the Flask app is running:")
        print(f"    python app.py")
        print(f"\n  Or update APP_BASE_URL in this script if your app is deployed elsewhere.")
        sys.exit(1)
    except Exception as e:
        print(f"✗ ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python trigger_backup.py [daily|monthly]")
        print("\nExamples:")
        print("  python trigger_backup.py daily")
        print("  python trigger_backup.py monthly")
        sys.exit(1)
    
    backup_type = sys.argv[1].lower()
    
    if backup_type not in ["daily", "monthly"]:
        print(f"Error: Invalid backup type '{backup_type}'")
        print("Must be either 'daily' or 'monthly'")
        sys.exit(1)
    
    trigger_backup(backup_type)
