# Promote the latest Airflow-trained model to the Kubernetes deployment.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\promote_model.ps1
$ErrorActionPreference = "Stop"

Write-Host "`n=== 1. Local model (trained by Airflow) ===" -ForegroundColor Cyan
Get-Content models\metrics.json

$POD = kubectl get pod -l app=btc-api --field-selector=status.phase=Running -o jsonpath="{.items[0].metadata.name}"
Write-Host "`n=== 2. Copying model to PVC via pod $POD ===" -ForegroundColor Cyan
kubectl cp models/model.pkl "${POD}:/app/models/model.pkl" -c btc-api
kubectl cp models/metrics.json "${POD}:/app/models/metrics.json" -c btc-api
kubectl exec $POD -c btc-api -- ls -la /app/models

Write-Host "`n=== 3. Rolling restart so every pod loads the new model ===" -ForegroundColor Cyan
kubectl rollout restart deployment btc-api
kubectl rollout status deployment btc-api

Write-Host "`n=== 4. Model now served by Kubernetes ===" -ForegroundColor Cyan
curl.exe -s http://btc-forecast.local/health
Write-Host ""