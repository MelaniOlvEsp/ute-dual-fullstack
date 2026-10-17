<#
Respaldo del piloto (C10, DP-11): volcado de PostgreSQL + documentos + manifiesto, todo en Drive (espacio `respaldos`).

  scripts\respaldo.ps1                          crea un respaldo (etiqueta semanal)
  scripts\respaldo.ps1 -Etiqueta periodo        antes de finalizar un período (o: depuracion, antes de depurar archivos)
  scripts\respaldo.ps1 -Orden listar            respaldos existentes
  scripts\respaldo.ps1 -Orden verificar -Id <id>  comprueba manifiesto, volcado y cada documento (SHA-256)
  scripts\respaldo.ps1 -Orden podar [-Aplicar]  retención: 8 más recientes + el más antiguo de cada uno de los 4 últimos meses

El volcado pasa por `.respaldo-tmp` (ignorada por git) y se elimina al terminar, también si algo falla.
La copia no se da por buena si la base referencia documentos que no están en el almacenamiento (código de salida 2).
No cifra la copia (decisión D3 de C10: solo con datos sintéticos; cifrar antes de usar datos reales).
#>
param(
    [ValidateSet('crear', 'listar', 'verificar', 'podar')][string]$Orden = 'crear',
    [ValidatePattern('^[a-z0-9]{1,20}$')][string]$Etiqueta = 'semanal',
    [string]$Id,
    [switch]$Aplicar,
    [string]$Proyecto = ''
)
$ErrorActionPreference = 'Continue'
Set-Location (Split-Path $PSScriptRoot -Parent)
$dc = @('compose'); if ($Proyecto) { $dc += @('-p', $Proyecto) }
$tmp = Join-Path (Get-Location) '.respaldo-tmp'
New-Item -ItemType Directory -Force $tmp | Out-Null

function Python($argumentos) {
    & docker @dc --profile respaldo run --rm --build respaldo python scripts/respaldo.py @argumentos | ForEach-Object { Write-Host $_ }
    return [int]$LASTEXITCODE
}

switch ($Orden) {
    'crear' {
        $archivo = Join-Path $tmp 'respaldo.dump'
        $antes = Join-Path $tmp 'antes.json'
        try {
            # Conteos y huella ANTES del volcado: la base restaurada debe quedar dentro del intervalo del manifiesto.
            if ((Python @('instantanea')) -ne 0) { Write-Error 'No se pudo tomar la instantánea previa.'; exit 1 }
            & docker @dc exec -T postgres sh -c 'PGPASSWORD=$APP_DB_PASSWORD pg_dump -h 127.0.0.1 -U ute_dual_app -d ute_dual_c01 -Fc -f /tmp/respaldo.dump'
            if ($LASTEXITCODE -ne 0) { Write-Error 'pg_dump falló.'; exit 1 }
            & docker @dc cp postgres:/tmp/respaldo.dump $archivo
            if ($LASTEXITCODE -ne 0) { Write-Error 'No se pudo copiar el volcado.'; exit 1 }
            $codigo = Python @('crear', '--volcado', '/tmp/respaldo/respaldo.dump', '--etiqueta', $Etiqueta)
        } finally {
            & docker @dc exec -T postgres rm -f /tmp/respaldo.dump | Out-Null
            Remove-Item -Force -ErrorAction SilentlyContinue $archivo
            Remove-Item -Force -ErrorAction SilentlyContinue $antes
        }
        exit $codigo
    }
    'listar' { exit (Python @('listar')) }
    'verificar' { if (-not $Id) { Write-Error 'Indica -Id.'; exit 1 }; exit (Python @('verificar', '--id', $Id)) }
    'podar' { exit (Python @(@('podar') + $(if ($Aplicar) { '--aplicar' } else { @() }))) }
}
