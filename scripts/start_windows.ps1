$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$python = Join-Path $root 'venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'venv not found. Create it with: py -m venv venv' }
& $python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Database migration failed. Make sure PostgreSQL is running and DATABASE_URL is correct.' }
& $python -m bot
