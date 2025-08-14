# Run accuracy test on Apple serial images

Write-Host "`n`n========== Testing OCR Accuracy ==========" -ForegroundColor Green

# Test with etched-dark preset (best for etched metal)
Write-Host "`nTesting with etched-dark preset..." -ForegroundColor Cyan
python scripts/accuracy_test.py --dir "Apple serial" --preset etched-dark

# Test with default preset
Write-Host "`nTesting with default preset..." -ForegroundColor Cyan
python scripts/accuracy_test.py --dir "Apple serial" --preset default

Write-Host "`n`nAccuracy testing complete." -ForegroundColor Green
