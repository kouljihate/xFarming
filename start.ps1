# xFarming startup script
Write-Host "Starting xFarming application..." -ForegroundColor Green
Set-Location D:\Projects\xFarming

# Check if MongoDB is running
$mongoRunning = Get-Process -Name "mongod" -ErrorAction SilentlyContinue
if (-not $mongoRunning) {
    Write-Host "Warning: MongoDB may not be running. Please start MongoDB first." -ForegroundColor Yellow
}

# Install dependencies if needed
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -q -r requirements.txt
}

# Activate venv and run
.\venv\Scripts\Activate.ps1
$env:FLASK_APP = "run.py"
$env:FLASK_ENV = "development"

Write-Host "Running xFarming on http://localhost:5000" -ForegroundColor Green
Write-Host "Login: admin / admin123" -ForegroundColor Cyan
python run.py
