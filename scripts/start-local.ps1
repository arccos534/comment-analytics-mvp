param(
    [switch]$SkipFrontend,
    [switch]$SkipBackend,
    [switch]$DemoMode
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"
$LocalDir = Join-Path $RepoRoot ".local"
$PgData = Join-Path $LocalDir "pgdata"
$PgLog = Join-Path $LocalDir "postgres-55432.log"
$DemoModeValue = "false"
if ($DemoMode.IsPresent) {
    $DemoModeValue = "true"
}

$Python311 = (Get-Command py -ErrorAction SilentlyContinue)
if (-not $Python311) {
    throw "Python launcher 'py' not found. Install Python 3.11 first."
}

$NodeExe = "C:\Program Files\nodejs\node.exe"
$NpmCmd = "C:\Program Files\nodejs\npm.cmd"
$PostgresBin = "C:\Program Files\PostgreSQL\16\bin"
$PgCtl = Join-Path $PostgresBin "pg_ctl.exe"
$InitDb = Join-Path $PostgresBin "initdb.exe"
$PgIsReady = Join-Path $PostgresBin "pg_isready.exe"
$Createdb = Join-Path $PostgresBin "createdb.exe"
$Psql = Join-Path $PostgresBin "psql.exe"

if (-not (Test-Path $NodeExe)) {
    throw "Node.js not found at $NodeExe"
}
if (-not (Test-Path $PgCtl)) {
    throw "PostgreSQL 16 not found at $PostgresBin"
}

New-Item -ItemType Directory -Force -Path $LocalDir | Out-Null

Write-Host "Checking local PostgreSQL cluster..."
if (-not (Test-Path $PgData)) {
    New-Item -ItemType Directory -Force -Path $PgData | Out-Null
    & $InitDb -D $PgData -U postgres -A trust --encoding=UTF8 --locale=C | Out-Host
}

& $PgIsReady -h 127.0.0.1 -p 55432 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Starting PostgreSQL on 127.0.0.1:55432..."
    Start-Process -FilePath $PgCtl `
        -ArgumentList @("start", "-D", $PgData, "-o", "`"-p 55432`"", "-l", $PgLog) `
        -WindowStyle Hidden | Out-Null
    Start-Sleep -Seconds 4
}

& $PgIsReady -h 127.0.0.1 -p 55432
if ($LASTEXITCODE -ne 0) {
    throw "PostgreSQL did not start on port 55432."
}

Write-Host "Ensuring database comment_analytics exists..."
& $Psql -h 127.0.0.1 -p 55432 -U postgres -d postgres -w -tAc "SELECT 1 FROM pg_database WHERE datname='comment_analytics'" | ForEach-Object {
    $script:DbExists = $_.Trim()
}
if ($DbExists -ne "1") {
    & $Createdb -h 127.0.0.1 -p 55432 -U postgres comment_analytics
}

$BackendPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
if (-not (Test-Path $BackendPython)) {
    Write-Host "Creating backend virtualenv..."
    Push-Location $BackendDir
    try {
        py -3.11 -m venv .venv
        & $BackendPython -m pip install --upgrade pip
        & $BackendPython -m pip install -r requirements.txt
    }
    finally {
        Pop-Location
    }
}

Write-Host "Running migrations..."
Push-Location $BackendDir
try {
    $env:DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:55432/comment_analytics"
    $env:REDIS_URL = "redis://localhost:6379/0"
    $env:DEMO_MODE = $DemoModeValue
    $env:BACKGROUND_JOBS_ENABLED = "false"
    & $BackendPython -m alembic upgrade head
}
finally {
    Pop-Location
}

if (-not $SkipBackend) {
    Write-Host "Starting backend on http://127.0.0.1:8000 ..."
    $backendCommand = @"
`$env:DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:55432/comment_analytics'
`$env:REDIS_URL='redis://localhost:6379/0'
`$env:DEMO_MODE='$DemoModeValue'
`$env:BACKGROUND_JOBS_ENABLED='false'
Set-Location '$BackendDir'
& '$BackendPython' -m uvicorn app.main:app --host 127.0.0.1 --port 8000
"@
    Start-Process powershell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendCommand)
}

if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Write-Host "Installing frontend dependencies..."
    Push-Location $FrontendDir
    try {
        $env:Path = "C:\Program Files\nodejs;" + $env:Path
        & $NpmCmd install
    }
    finally {
        Pop-Location
    }
}

if (-not $SkipFrontend) {
    Write-Host "Starting frontend on http://127.0.0.1:3000 ..."
    $frontendCommand = @"
`$env:Path='C:\Program Files\nodejs;' + `$env:Path
`$env:NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:8000/api/v1'
Set-Location '$FrontendDir'
& '$NpmCmd' run dev
"@
    Start-Process powershell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontendCommand)
}

Write-Host ""
Write-Host "Ready:"
Write-Host "  Frontend: http://127.0.0.1:3000"
Write-Host "  Backend:  http://127.0.0.1:8000"
Write-Host "  Docs:     http://127.0.0.1:8000/docs"
Write-Host ""
if ($DemoMode.IsPresent) {
    Write-Host "Demo sources:"
    Write-Host "  https://t.me/demo_channel"
    Write-Host "  https://t.me/demo_channel/100"
    Write-Host "  https://vk.com/democommunity"
    Write-Host "  https://vk.com/wall-1_123"
} else {
    Write-Host "Live mode is enabled."
    Write-Host "Set TELEGRAM_API_ID / TELEGRAM_API_HASH / TELEGRAM_SESSION_STRING and VK_API_TOKEN in your environment before indexing."
}
