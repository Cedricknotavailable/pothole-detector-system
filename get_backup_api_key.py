#!/usr/bin/env python3
"""Script to retrieve the backup API key from the database."""

from app import app, db, Settings

with app.app_context():
    api_key_setting = Settings.query.filter_by(key='backup_api_key').first()
    
    if api_key_setting:
        print(f"Backup API Key: {api_key_setting.value}")
        print("\nYou need to set this in your GitHub repository secrets:")
        print("1. Go to your GitHub repository")
        print("2. Settings → Secrets and variables → Actions")
        print("3. Add/Update secret: BACKUP_API_KEY")
        print(f"4. Value: {api_key_setting.value}")
    else:
        print("No backup API key found in database.")
        print("The key will be generated when the app starts.")
