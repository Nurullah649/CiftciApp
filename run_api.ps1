# API'yi doğru kökten başlatır (app paketi bu klasörün altında)
Set-Location $PSScriptRoot
Write-Host "Çalışma dizini: $(Get-Location)" -ForegroundColor Cyan
Write-Host "Komut: uvicorn app.main:app --host 0.0.0.0 --port 8000" -ForegroundColor Cyan
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
