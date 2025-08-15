# Run memory-efficient test on Apple serial images

Write-Host "`n========== Running Memory-Efficient OCR Test ==========" -ForegroundColor Green

# Run the test
python scripts/test_memory_efficient.py

Write-Host "`nTest complete. Results saved to reports/memory_efficient_results.csv" -ForegroundColor Green
Write-Host "Debug images saved to exports/debug/memory_efficient" -ForegroundColor Green
