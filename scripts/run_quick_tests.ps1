# Run quick tests on sample images with different presets

# Create exports directory if it doesn't exist
$exportsDir = "exports/debug"
if (-not (Test-Path $exportsDir)) {
    New-Item -Path $exportsDir -ItemType Directory -Force
}

# Test with etched-dark preset
Write-Host "`n`n========== Testing with etched-dark preset ==========" -ForegroundColor Green
python scripts/quick_test.py --image "Apple serial/IMG-20250813-WA0024.jpg" --preset etched-dark

# Check if the test was successful
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Test failed with etched-dark preset. Continuing with other tests..." -ForegroundColor Yellow
}

# Test with etched preset
Write-Host "`n`n========== Testing with etched preset ==========" -ForegroundColor Green
python scripts/quick_test.py --image "Apple serial/IMG-20250813-WA0025.jpg" --preset etched

# Check if the test was successful
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Test failed with etched preset. Continuing with other tests..." -ForegroundColor Yellow
}

# Test with sticker preset
Write-Host "`n`n========== Testing with sticker preset ==========" -ForegroundColor Green
python scripts/quick_test.py --image "Apple serial/IMG-20250813-WA0026.jpg" --preset sticker

# Check if the test was successful
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Test failed with sticker preset. Continuing with other tests..." -ForegroundColor Yellow
}

# Test with screen preset
Write-Host "`n`n========== Testing with screen preset ==========" -ForegroundColor Green
python scripts/quick_test.py --image "Apple serial/IMG-20250813-WA0027.jpg" --preset screen

# Check if the test was successful
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Test failed with screen preset. Continuing with other tests..." -ForegroundColor Yellow
}

# Test with default preset
Write-Host "`n`n========== Testing with default preset ==========" -ForegroundColor Green
python scripts/quick_test.py --image "Apple serial/IMG-20250813-WA0028.jpg" --preset default

# Check if the test was successful
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Test failed with default preset. Continuing with other tests..." -ForegroundColor Yellow
}

Write-Host "`n`nAll tests complete. Check the exports/debug directory for debug images." -ForegroundColor Cyan
