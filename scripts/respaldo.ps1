<#
Respaldo del piloto (C10, DP-11; cifrado en C13): volcado de PostgreSQL + documentos + manifiesto, todo CIFRADO con age y en
Drive (espacio `respaldos`). La máquina solo conoce la clave pública; la clave privada la guarda el responsable fuera del equipo.

  scripts\respaldo.ps1 -Orden generar-clave -Salida <ruta>   (una sola vez) crea el par de claves: la privada va a <ruta> (fuera del
                                                              repositorio y de Drive) y la pública a .secretos\respaldo_clave_publica.txt
  scripts\respaldo.ps1                          crea un respaldo cifrado (etiqueta semanal)
  scripts\respaldo.ps1 -Etiqueta periodo        antes de finalizar un período (o: depuracion, antes de depurar archivos)
  scripts\respaldo.ps1 -SinCifrar               SOLO con datos sintéticos: respaldo sin cifrar
  scripts\respaldo.ps1 -Orden listar            respaldos existentes (cifrado / SIN CIFRAR)
  scripts\respaldo.ps1 -Orden verificar -Id <id>  comprueba manifiesto, volcado y cada documento por su SHA-256 (sin la clave)
  scripts\respaldo.ps1 -Orden verificar -Id <id> -Identidad <ruta>   además descifra y compara el contenido (con la clave privada)
  scripts\respaldo.ps1 -Orden podar [-Aplicar]  retención: 8 más recientes + el más antiguo de cada uno de los 4 últimos meses

El volcado pasa por `.respaldo-tmp` (ignorada por git) y se elimina al terminar, también si algo falla; lo mismo la copia
temporal de la clave privada. La copia no se da por buena si la base referencia documentos que no están en el almacenamiento
(código de salida 2). Sin clave pública el respaldo se rechaza (código 1): el cifrado es obligatorio salvo -SinCifrar.
#>
param(
    [ValidateSet('crear', 'listar', 'verificar', 'podar', 'generar-clave')][string]$Orden = 'crear',
    [ValidatePattern('^[a-z0-9]{1,20}$')][string]$Etiqueta = 'semanal',
    [string]$Id,
    [switch]$Aplicar,
    [switch]$SinCifrar,
    [string]$Salida,
    [string]$Identidad,
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
    'generar-clave' {
        if (-not $Salida) { Write-Error 'Indica -Salida con la ruta (fuera del repositorio) donde guardar la clave privada.'; exit 1 }
        $publica = Join-Path (Get-Location) '.secretos\respaldo_clave_publica.txt'
        if ((Test-Path -LiteralPath $Salida) -or (Test-Path -LiteralPath $publica)) {
            Write-Error 'Ya existe una clave: la ruta indicada en -Salida o el archivo .secretos\respaldo_clave_publica.txt. No se sobrescribe (se perdería la forma de restaurar). Para crear un par nuevo, usa otra ruta en -Salida y antes cambia de nombre .secretos\respaldo_clave_publica.txt (por ejemplo a respaldo_clave_publica.2026-10-17.txt; no lo borres mientras existan respaldos hechos con esa clave). Pasos completos: guía de operación, sección 6.1.'; exit 1
        }
        $privada = Join-Path $tmp 'identidad-nueva.txt'
        try {
            if ((Python @('generar-clave')) -ne 0) { Write-Error 'No se pudo generar el par de claves.'; exit 1 }
            New-Item -ItemType Directory -Force (Split-Path -Parent $Salida) | Out-Null
            Move-Item -LiteralPath $privada -Destination $Salida
            New-Item -ItemType Directory -Force (Join-Path (Get-Location) '.secretos') | Out-Null
            Copy-Item -LiteralPath (Join-Path $tmp 'clave_publica.txt') -Destination $publica
            # Solo el usuario actual puede leer la clave privada (se quitan los permisos heredados).
            & icacls $Salida /inheritance:r /grant:r "$($env:USERNAME):(R,W)" | Out-Null
        } finally {
            Remove-Item -Force -ErrorAction SilentlyContinue $privada
            Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $tmp 'clave_publica.txt')
        }
        Write-Host "Clave privada guardada en: $Salida"
        Write-Host 'GUÁRDALA FUERA DE ESTE EQUIPO y de Drive (por ejemplo en un gestor de contraseñas y una copia impresa o en una memoria USB sellada).'
        Write-Host 'Sin esta clave NO se puede restaurar ningún respaldo cifrado. La clave pública quedó en .secretos\respaldo_clave_publica.txt.'
        exit 0
    }
    'crear' {
        $archivo = Join-Path $tmp 'respaldo.dump'
        $antes = Join-Path $tmp 'antes.json'
        $extra = if ($SinCifrar) { @('--sin-cifrar') } else { @() }
        try {
            # Conteos y huella ANTES del volcado: la base restaurada debe quedar dentro del intervalo del manifiesto.
            if ((Python @('instantanea')) -ne 0) { Write-Error 'No se pudo tomar la instantánea previa.'; exit 1 }
            & docker @dc exec -T postgres sh -c 'PGPASSWORD=$APP_DB_PASSWORD pg_dump -h 127.0.0.1 -U ute_dual_app -d ute_dual_c01 -Fc -f /tmp/respaldo.dump'
            if ($LASTEXITCODE -ne 0) { Write-Error 'pg_dump falló.'; exit 1 }
            & docker @dc cp postgres:/tmp/respaldo.dump $archivo
            if ($LASTEXITCODE -ne 0) { Write-Error 'No se pudo copiar el volcado.'; exit 1 }
            $codigo = Python (@('crear', '--volcado', '/tmp/respaldo/respaldo.dump', '--etiqueta', $Etiqueta) + $extra)
        } finally {
            & docker @dc exec -T postgres rm -f /tmp/respaldo.dump | Out-Null
            Remove-Item -Force -ErrorAction SilentlyContinue $archivo
            Remove-Item -Force -ErrorAction SilentlyContinue $antes
        }
        exit $codigo
    }
    'listar' { exit (Python @('listar')) }
    'verificar' {
        if (-not $Id) { Write-Error 'Indica -Id.'; exit 1 }
        $copia = Join-Path $tmp 'identidad.txt'
        $extra = @()
        try {
            if ($Identidad) {
                if (-not (Test-Path -LiteralPath $Identidad)) { Write-Error 'No existe el archivo de clave privada indicado en -Identidad.'; exit 1 }
                Copy-Item -LiteralPath $Identidad -Destination $copia
                $extra = @('--con-clave')
            }
            $codigo = Python (@('verificar', '--id', $Id) + $extra)
        } finally {
            Remove-Item -Force -ErrorAction SilentlyContinue $copia
        }
        exit $codigo
    }
    'podar' { exit (Python @(@('podar') + $(if ($Aplicar) { '--aplicar' } else { @() }))) }
}
