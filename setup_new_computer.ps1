# AutoClean Quick Setup Script for New Computer
# Run this script to set up AutoClean on a fresh machine

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AutoClean Setup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found! Please install Python 3.11+ from python.org" -ForegroundColor Red
    exit 1
}

# Check Node.js
Write-Host "Checking Node.js installation..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    Write-Host "✓ Node.js found: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Node.js not found! Please install from nodejs.org" -ForegroundColor Red
    exit 1
}

# Check npm
Write-Host "Checking npm installation..." -ForegroundColor Yellow
try {
    $npmVersion = npm --version 2>&1
    Write-Host "✓ npm found: v$npmVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ npm not found! Please install Node.js (npm comes with it)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
python -m venv venv
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to create virtual environment" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Virtual environment created" -ForegroundColor Green

Write-Host ""
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

Write-Host ""
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
Write-Host "✓ pip upgraded" -ForegroundColor Green

Write-Host ""
Write-Host "Installing Python dependencies (this may take 5-10 minutes)..." -ForegroundColor Yellow
pip install -r backend\app\requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to install Python dependencies" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Python dependencies installed" -ForegroundColor Green

Write-Host ""
Write-Host "Initializing database..." -ForegroundColor Yellow
python init_db.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to initialize database" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Database initialized" -ForegroundColor Green

Write-Host ""
Write-Host "Installing frontend dependencies (this may take 2-5 minutes)..." -ForegroundColor Yellow
Set-Location frontend
npm install
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to install frontend dependencies" -ForegroundColor Red
    Set-Location ..
    exit 1
}
Write-Host "✓ Frontend dependencies installed" -ForegroundColor Green
Set-Location ..

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Create .env file:" -ForegroundColor White
Write-Host "   - Copy .env.example to .env" -ForegroundColor Gray
Write-Host "   - Add your OPENAI_API_KEY" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Start backend server (Terminal 1):" -ForegroundColor White
Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "   python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Start frontend server (Terminal 2):" -ForegroundColor White
Write-Host "   cd frontend" -ForegroundColor Gray
Write-Host "   npm run dev" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Open browser:" -ForegroundColor White
Write-Host "   http://localhost:3000" -ForegroundColor Gray
Write-Host ""










