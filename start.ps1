# Opportunity Agent - start backend + frontend
Set-Location $PSScriptRoot

# Check .env
if (-not (Test-Path "backend\.env")) {
    Write-Host "No .env found. Copying from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" "backend\.env"
    Write-Host "Edit backend\.env and add your ANTHROPIC_API_KEY, then re-run." -ForegroundColor Yellow
    exit 1
}

# Install backend deps
Write-Host "Installing backend dependencies..." -ForegroundColor Cyan
Set-Location backend
pip install -r requirements.txt -q
Set-Location ..

# Install frontend deps
Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
Set-Location frontend
npm install --silent
Set-Location ..

Write-Host ""
Write-Host "Starting Opportunity Agent..." -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8010" -ForegroundColor White
Write-Host "  Frontend: http://localhost:5120" -ForegroundColor White
Write-Host ""

# Start backend in background
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot\backend'; uvicorn app:app --reload --port 8010" -WindowStyle Normal

# Start frontend
Set-Location frontend
npm run dev
