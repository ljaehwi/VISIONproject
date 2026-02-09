param(
  [int]$DbPort = 5344,
  [string]$BackendHost = '0.0.0.0',
  [int]$BackendPort = 8000
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# Start only the DB container
& docker-compose up -d db

# Wait for DB to be ready
$maxWait = 60
$elapsed = 0
Write-Host "Waiting for DB to be ready..."
while ($true) {
  $ready = & docker-compose exec -T db pg_isready -U aca -d aca 2>$null
  if ($LASTEXITCODE -eq 0) { break }
  Start-Sleep -Seconds 2
  $elapsed += 2
  if ($elapsed -ge $maxWait) {
    throw "DB did not become ready within $maxWait seconds."
  }
}
Write-Host "DB is ready."

# Point backend to local forwarded DB port
$env:DATABASE_URL = "postgresql+asyncpg://aca:aca@localhost:$DbPort/aca"

# Run backend
& uvicorn app.main:app --host $BackendHost --port $BackendPort
