#!/bin/bash
# Script to manually trigger a daily backup

# Replace with your actual app URL (e.g., https://your-app.onrender.com or http://localhost:5000)
APP_BASE_URL="http://localhost:5000"

# Your backup API key
BACKUP_API_KEY="ae3784f4ecd2960e7fe3ad2a58a84469b257ee60f808f5188245080ad85e8508"

echo "Triggering daily backup..."
echo "URL: ${APP_BASE_URL}/api/backups/scheduled"
echo ""

curl --fail -X POST \
  -H "X-Backup-Api-Key: ${BACKUP_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"type":"daily"}' \
  ${APP_BASE_URL}/api/backups/scheduled

echo ""
echo "Done!"
