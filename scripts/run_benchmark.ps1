# Run benchmark with optimized parameters
param(
    [string]$Dir = "exported-assets",
    [string]$ApiUrl = "http://localhost:8000",
    [string]$OutputCsv = "exports/benchmark_results.csv",
    [switch]$UseBinary = $false,
    [switch]$UseGpu = $true
)

# Find curl.exe or use Invoke-WebRequest
$curl = Get-Command "curl.exe" -ErrorAction SilentlyContinue
if (-not $curl) {
    Write-Host "curl.exe not found, using Invoke-WebRequest"
    $curl = "Invoke-WebRequest"
}

# Create output directory if it doesn't exist
$outputDir = Split-Path -Parent $OutputCsv
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

# Create CSV header
"filename,serial,confidence" | Out-File -FilePath $OutputCsv -Encoding utf8

# Get image files
$imageFiles = Get-ChildItem -Path $Dir -Filter "*.jpeg" | Sort-Object Name

# Set mode based on UseBinary flag
$mode = if ($UseBinary) { "binary" } else { "gray" }

# Set parameters
$params = @{
    "min_confidence" = "0.0"
    "persist" = "false"
    "mode" = $mode
    "upscale_scale" = "4.5"
    "roi" = "true"
    "roi_top_k" = "3"
    "roi_pad" = "12"
    "adaptive_pad" = "true"
    "glare_reduction" = "adaptive"
    "low_text" = "0.15"
    "text_threshold" = "0.35"
    "mag_ratio" = "1.2"
    "rotations" = "0,90,180,270"
}

# Build query string
$queryString = ($params.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "&"

# Process each image
$total = $imageFiles.Count
$detected = 0
$i = 0

foreach ($file in $imageFiles) {
    $i++
    Write-Host "Processing $($file.Name) ($i/$total)..."
    
    try {
        if ($curl -eq "Invoke-WebRequest") {
            # Using Invoke-WebRequest
            $response = Invoke-WebRequest -Uri "$ApiUrl/process-serial?$queryString" -Method Post -Form @{image=Get-Item -Path $file.FullName} -UseBasicParsing | ConvertFrom-Json
        } else {
            # Using curl.exe
            $curlCmd = "& $curl -s -X POST `"$ApiUrl/process-serial?$queryString`" -F `"image=@$($file.FullName)`""
            $responseJson = Invoke-Expression $curlCmd
            $response = $responseJson | ConvertFrom-Json
        }
        
        if ($response.serials.Count -gt 0) {
            $detected++
            $topSerial = $response.serials[0]
            "$($file.Name),$($topSerial.serial),$($topSerial.confidence)" | Out-File -FilePath $OutputCsv -Append -Encoding utf8
            Write-Host "  Detected: $($topSerial.serial) (confidence: $($topSerial.confidence))" -ForegroundColor Green
        } else {
            "$($file.Name),," | Out-File -FilePath $OutputCsv -Append -Encoding utf8
            Write-Host "  No serial detected" -ForegroundColor Red
        }
    } catch {
        Write-Host "  Error processing $($file.Name): $_" -ForegroundColor Red
        "$($file.Name),ERROR," | Out-File -FilePath $OutputCsv -Append -Encoding utf8
    }
}

# Print summary
Write-Host ""
Write-Host "Benchmark complete!" -ForegroundColor Cyan
Write-Host "Total images: $total" -ForegroundColor Cyan
Write-Host "Detected serials: $detected ($([math]::Round($detected/$total*100, 2))%)" -ForegroundColor Cyan
Write-Host "Results saved to: $OutputCsv" -ForegroundColor Cyan
