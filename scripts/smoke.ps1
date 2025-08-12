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

function Invoke-ProcessSerial($imgPath) {
  $supportsForm = (Get-Command Invoke-WebRequest).Parameters.ContainsKey('Form')
  if ($supportsForm) {
    $form = @{ image = Get-Item $imgPath }
    return (Invoke-WebRequest -Uri http://localhost:8000/process-serial -Method Post -Form $form).Content
  } else {
    $curl = Join-Path $env:SystemRoot 'System32/curl.exe'
    if (-not (Test-Path $curl)) {
      throw "curl.exe not found; install curl or run in PowerShell 7+ for -Form support"
    }
    $out = & $curl -s -X POST http://localhost:8000/process-serial -F "image=@$imgPath"
    return $out
  }
}

if ($ImagePath -and (Test-Path $ImagePath)) {
  Write-Host "[Smoke] Testing /process-serial with: $ImagePath"
  try {
    $resp = Invoke-ProcessSerial -imgPath $ImagePath
    Write-Host "[Smoke] Process response: $resp"
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
