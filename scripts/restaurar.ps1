<#
Restauración de prueba del piloto (C10, AC-24): NUNCA sobre la base ni la carpeta vivas.

  scripts\restaurar.ps1 -Id <id> [-Registro <id>] [-Descartar]

1. Verifica el respaldo (manifiesto, volcado y cada documento por SHA-256); si no está íntegro, se rechaza.
2. Crea una carpeta de Drive nueva («Formación Dual (restauración …)») y un proyecto de Compose aparte
   (`c10-restauracion`: base nueva, API en el puerto 8101).
3. Comprueba el volcado con `pg_restore --list`; si está dañado, se rechaza. Restaura la base nueva.
4. Copia los documentos a la carpeta nueva y vuelve a aplicar el registro de depuraciones del respaldo más reciente
   (o de -Registro): lo eliminado a propósito no reaparece.
5. Verifica conteos, huellas de notas y revisiones, que cada documento no archivado exista con su SHA-256 y descarga
   por la API restaurada una muestra de originales y firmados.
-Descartar elimina después el proyecto de prueba (volúmenes) y la carpeta de restauración de Drive.
Las credenciales de Drive se leen de `.secretos`; los identificadores no se imprimen.
#>
param(
    [Parameter(Mandatory = $true)][ValidatePattern('^\d{8}T\d{6}Z-[a-z0-9]{1,20}$')][string]$Id,
    [string]$Registro = '',
    [switch]$Descartar,
    [string]$Identidad = '',
    [string]$ProyectoOrigen = ''
)
$ErrorActionPreference = 'Continue'
Set-Location (Split-Path $PSScriptRoot -Parent)
$origen = @('compose'); if ($ProyectoOrigen) { $origen += @('-p', $ProyectoOrigen) }
$prueba = @('compose', '-p', 'c10-restauracion')
$tmp = Join-Path (Get-Location) '.respaldo-tmp'
New-Item -ItemType Directory -Force $tmp | Out-Null

function Origen-Python($argumentos) { & docker @origen --profile respaldo run --rm --build respaldo python scripts/respaldo.py @argumentos | ForEach-Object { Write-Host $_ }; return [int]$LASTEXITCODE }
function Prueba-Python($argumentos) { & docker @prueba --profile respaldo run --rm --build respaldo python scripts/respaldo.py @argumentos | ForEach-Object { Write-Host $_ }; return [int]$LASTEXITCODE }
$script:destinoCreado = $false
function Limpiar-Temporales { Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $tmp 'restaurar.dump') }
# La copia temporal de la clave privada se necesita también para restaurar los documentos: se borra solo al terminar o al fallar.
function Limpiar-Identidad { Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $tmp 'identidad.txt') }
function Descartar-Destino {
    if ($Descartar -and $script:destinoCreado) {
        Prueba-Python @('descartar-carpeta') | Out-Null
        & docker @prueba down -v | Out-Null
        Write-Host 'Proyecto de prueba y carpeta de restauración eliminados.'
    }
}
function Fallar($mensaje, $codigo = 2) { Write-Host "RESTAURACIÓN RECHAZADA: $mensaje"; Limpiar-Temporales; Limpiar-Identidad; Descartar-Destino; exit $codigo }

# Identificador de la carpeta viva (solo en memoria): variable de entorno o .secretos\drive_config.json.
$vivo = $env:DRIVE_CARPETA_ID
if (-not $vivo -and (Test-Path .secretos\drive_config.json)) { $vivo = (Get-Content .secretos\drive_config.json -Raw | ConvertFrom-Json).carpeta_id }
if (-not $vivo) { Write-Error 'No se encontró la carpeta de Drive de origen.'; exit 1 }
$env:RESPALDO_ORIGEN_CARPETA = $vivo

# Clave privada (solo si el respaldo está cifrado): se copia a la carpeta temporal y se borra al terminar, también si algo falla.
if ($Identidad) {
    if (-not (Test-Path -LiteralPath $Identidad)) { Fallar 'no existe el archivo de clave privada indicado en -Identidad.' 1 }
    Copy-Item -LiteralPath $Identidad -Destination (Join-Path $tmp 'identidad.txt')
}

# 1. Verificación y descarga del volcado (en el entorno de origen, de solo lectura); si está cifrado, se descifra aquí.
if ((Origen-Python @('descargar-volcado', '--id', $Id)) -ne 0) { Fallar 'el respaldo no está íntegro o falta la clave privada correcta (use -Identidad).' }

# 2. Destino aislado: carpeta de Drive nueva y proyecto de Compose aparte.
if ((Origen-Python @('carpeta-restauracion')) -ne 0) { Fallar 'no se pudo crear la carpeta de destino.' 1 }
$script:destinoCreado = $true
$env:RESPALDO_ENTORNO = 'restauracion'   # habilita los subcomandos que escriben en el destino aislado
$env:DRIVE_CARPETA_ID = (Get-Content (Join-Path $tmp 'destino.id') -Raw).Trim()
$env:API_PORT = '8101'
& docker @prueba up -d --wait postgres api
if ($LASTEXITCODE -ne 0) { Fallar 'no arrancó el proyecto de prueba.' 1 }

# 3. Volcado: comprobación y restauración sobre la base NUEVA.
& docker @prueba cp (Join-Path $tmp 'restaurar.dump') postgres:/tmp/restaurar.dump
& docker @prueba exec -T postgres sh -c 'pg_restore --list /tmp/restaurar.dump > /dev/null'
if ($LASTEXITCODE -ne 0) { Fallar 'el volcado está dañado (pg_restore --list falló); la base de prueba no se tocó.' }
& docker @prueba exec -T postgres sh -c 'PGPASSWORD=$APP_DB_PASSWORD pg_restore -h 127.0.0.1 -U ute_dual_app -d ute_dual_c01 --clean --if-exists --no-owner --no-privileges --single-transaction --exit-on-error /tmp/restaurar.dump'
if ($LASTEXITCODE -ne 0) { Fallar 'pg_restore falló.' }
& docker @prueba exec -T postgres rm -f /tmp/restaurar.dump | Out-Null
Limpiar-Temporales

# 4 y 5. Documentos, registro de depuraciones y verificación.
$extra = if ($Registro) { @('--registro', $Registro) } else { @() }
$codigo = Prueba-Python (@('restaurar-documentos', '--id', $Id) + $extra)
if ($codigo -eq 0) {
    & docker @prueba restart api | Out-Null
    & docker @prueba up -d --wait api | Out-Null
    $codigo = Prueba-Python (@('verificar-restauracion', '--id', $Id) + $extra)
}

Limpiar-Temporales
Limpiar-Identidad
Descartar-Destino
exit $codigo
