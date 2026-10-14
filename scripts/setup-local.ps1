# Genera solo .env raíz para Compose; no modifica configuraciones existentes.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot '.env'
if (Test-Path -LiteralPath $envPath) {
    Write-Output '.env ya existe: se conserva sin cambios.'
    exit 0
}
function New-LocalSecret {
    $bytes = New-Object byte[] 48
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
    return [Convert]::ToBase64String($bytes).Replace('+','-').Replace('/','_').TrimEnd('=')
}
$settingsText = @(
    "POSTGRES_PASSWORD=$(New-LocalSecret)"
    "APP_DB_PASSWORD=$(New-LocalSecret)"
    "SECRET_KEY=$(New-LocalSecret)"
    'WEB_PORT=5174'
    'API_PORT=8001'
)
[System.IO.File]::WriteAllLines($envPath, $settingsText, (New-Object System.Text.UTF8Encoding($false)))
Write-Output '.env creado con secretos aleatorios. No compartir ni versionar.'
