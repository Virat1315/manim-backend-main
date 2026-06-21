$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Test-Redis {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", 6379)
        $tcp.Close()
        return $true
    } catch {
        return $false
    }
}

Write-Host "==> Mentrax Manim Backend deployment" -ForegroundColor Cyan

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example - add your API keys before production use." -ForegroundColor Yellow
}

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Green
    python -m venv .venv
}

Write-Host "Installing Python dependencies..." -ForegroundColor Green
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\pip.exe install -r requirements.txt

New-Item -ItemType Directory -Force -Path uploads, CONTENT, media, temp_audios | Out-Null

if (-not (Test-Redis)) {
    Write-Host "Redis is not running on port 6379." -ForegroundColor Yellow
    $redisExe = "${env:ProgramFiles}\Redis\redis-server.exe"
    if (Test-Path $redisExe) {
        Write-Host "Starting Redis..." -ForegroundColor Green
        Start-Process -FilePath $redisExe -WindowStyle Hidden
        Start-Sleep -Seconds 2
    } else {
        Write-Host "Install Redis with: winget install Redis.Redis" -ForegroundColor Red
        Write-Host "Or start Redis manually, then re-run this script." -ForegroundColor Red
        exit 1
    }
}

if (-not (Test-Redis)) {
    Write-Host "Redis still unavailable. Aborting." -ForegroundColor Red
    exit 1
}

Write-Host "Starting Celery worker..." -ForegroundColor Green
Start-Process -FilePath ".\.venv\Scripts\celery.exe" `
    -ArgumentList "-A gen_topic.celery_app worker --loglevel=info --pool=solo" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden

Write-Host "Starting FastAPI server on http://0.0.0.0:8000" -ForegroundColor Green
& .\.venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8000
