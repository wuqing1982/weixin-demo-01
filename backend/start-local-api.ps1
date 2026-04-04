param(
  [string]$Host = "127.0.0.1",
  [int]$Port = 8000
)

Set-Location $PSScriptRoot
if (-not $env:PUBLIC_BASE_URL) {
  $env:PUBLIC_BASE_URL = "https://e.cps.vin"
}
python -m uvicorn app.main:app --reload --host $Host --port $Port
