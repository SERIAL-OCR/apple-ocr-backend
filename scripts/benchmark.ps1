param(
  [Parameter(Mandatory=$true)] [string]$Dir,
  [double]$MinConfidence = 0.0,
  [string]$ExtraQuery = ""
)

if (-not (Test-Path $Dir)) {
  Write-Error "Directory not found: $Dir"
  exit 1
}

$files = Get-ChildItem -Path $Dir -File -Recurse -Include *.jpg,*.jpeg,*.png,*.heic,*.heif
if ($files.Count -eq 0) {
  Write-Error "No images found under: $Dir"
  exit 1
}

function Invoke-ProcessSerial($imgPath, $minConf, $extra) {
  $supportsForm = (Get-Command Invoke-WebRequest).Parameters.ContainsKey('Form')
  $qs = "min_confidence=$minConf"
  if ($extra -and $extra.Trim().Length -gt 0) { $qs = "$qs&$extra" }
  if ($supportsForm) {
    $form = @{ image = Get-Item $imgPath }
    $resp = Invoke-WebRequest -Uri "http://localhost:8000/process-serial?$qs" -Method Post -Form $form
    return $resp.Content
  } else {
    $curl = Join-Path $env:SystemRoot 'System32/curl.exe'
    if (-not (Test-Path $curl)) { throw "curl.exe not found; install curl or run in PowerShell 7+ for -Form support" }
    $out = & $curl -s -X POST "http://localhost:8000/process-serial?$qs" -F "image=@$imgPath"
    return $out
  }
}

$ok = 0
$total = 0
$fail = 0

foreach ($f in $files) {
  $total++
  try {
    $raw = Invoke-ProcessSerial -imgPath $f.FullName -minConf $MinConfidence -extra $ExtraQuery
    $json = $raw | ConvertFrom-Json
    if ($null -ne $json -and $json.serials -and $json.serials.Count -gt 0) { $ok++ } else { $fail++ }
    Write-Host "[OK] $($f.Name): $($json.serials | ConvertTo-Json -Compress)"
  } catch {
    $fail++
    Write-Warning "[FAIL] $($f.Name): $_"
  }
}

Write-Host "---"
Write-Host "Total: $total  OK: $ok  FAIL/Empty: $fail"
