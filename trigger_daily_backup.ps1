# PowerShell script to manually trigger a daily backup

# Replace with your actual app URL (e.g., https://your-app.onrender.com or http://localhost:5000)
$APP_BASE_URL = "http://172.24.156.42:8000"

# Your backup API key
$BACKUP_API_KEY = "ae3784f4ecd2960e7fe3ad2a58a84469b257ee60f808f5188245080ad85e8508"

Write-Host "Triggering daily backup..." -ForegroundColor Cyan
Write-Host "URL: $APP_BASE_URL/api/backups/scheduled"
Write-Host ""

try {
    $response = Invoke-WebRequest -Uri "$APP_BASE_URL/api/backups/scheduled" `
        -Method POST `
        -Headers @{
            "X-Backup-Api-Key" = $BACKUP_API_KEY
            "Content-Type" = "application/json"
        } `
        -Body '{"type":"daily"}' `
        -UseBasicParsing

    Write-Host "Success!" -ForegroundColor Green
    Write-Host "Status Code: $($response.StatusCode)"
    Write-Host "Response: $($response.Content)"
}
catch {
    Write-Host "Error!" -ForegroundColor Red
    Write-Host $_.Exception.Message
}

Write-Host ""
Write-Host "Done!"
