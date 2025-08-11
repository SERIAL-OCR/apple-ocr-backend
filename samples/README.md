## Samples

Place test images here to try the OCR endpoint.

### Test with curl (Git Bash / WSL)
```
curl -X POST http://localhost:8000/process-serial \
  -F "image=@samples/your_image.jpg"
```

### Test with PowerShell
```
$Form = @{ image = Get-Item .\samples\your_image.jpg }
Invoke-WebRequest -Uri http://localhost:8000/process-serial -Method Post -Form $Form | Select-Object -ExpandProperty Content
```

### Export Excel
```
curl -o exports/serials.xlsx http://localhost:8000/export
```
