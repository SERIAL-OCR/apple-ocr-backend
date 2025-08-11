param(
  [string]$ImagePath = ""
)

Write-Host "[Smoke] Checking /health..."
try {
  $health = Invoke-RestMethod -Uri http://localhost:8000/health -Method Get
  Write-Host "[Smoke] Health: $($health | ConvertTo-Json -Compress)"
} catch {
  Write-Error "[Smoke] Health check failed: $_"
}

if ($ImagePath -and (Test-Path $ImagePath)) {
  Write-Host "[Smoke] Testing /process-serial with: $ImagePath"
  try {
    $form = @{ image = Get-Item $ImagePath }
    $resp = Invoke-WebRequest -Uri http://localhost:8000/process-serial -Method Post -Form $form
    Write-Host "[Smoke] Process response: $($resp.Content)"
  } catch {
    Write-Error "[Smoke] Process-serial failed: $_"
  }
} else {
  Write-Host "[Smoke] Skipping /process-serial (no image provided)"
}

Write-Host "[Smoke] Downloading /export..."
try {
  New-Item -ItemType Directory -Path exports -Force | Out-Null
  Invoke-WebRequest -Uri http://localhost:8000/export -OutFile .\exports\serials_smoke.xlsx
  Write-Host "[Smoke] Export saved to .\\exports\\serials_smoke.xlsx"
} catch {
  Write-Error "[Smoke] Export failed: $_"
}
