import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, relative } from 'node:path'

// C17: los botones de acción tienen UNA definición (global.css, con los valores de la base original) y ninguna pantalla
// vuelve a definirlos con estilos locales. Evita que reaparezcan botones «distintos» en cada pantalla.
const raiz = join(dirname(fileURLToPath(import.meta.url)), '..', 'src')
const css = readFileSync(join(raiz, 'global.css'), 'utf8')

const KIT = ['btn-primary', 'btn-outline', 'btn-danger', 'btn-danger-outline', 'btn-link', 'btn-back', 'btn-sm', 'btn-auto']
const RETIRADOS = ['btn-revisar', 'btn-ver', 'btn-eliminar']

function archivos(dir) {
  return readdirSync(dir).flatMap((nombre) => {
    const ruta = join(dir, nombre)
    return statSync(ruta).isDirectory() ? archivos(ruta) : ruta.endsWith('.svelte') ? [ruta] : []
  })
}

function estilos(texto) {
  return [...texto.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)].map((m) => m[1]).join('\n')
}

function regla(selector) {
  const inicio = css.search(new RegExp(`(^|\\n)${selector.replace(/[-.]/g, '\\$&')}\\s*\\{`))
  assert.ok(inicio >= 0, `global.css no define ${selector}`)
  return css.slice(inicio, css.indexOf('}', inicio))
}

test('global.css define el kit completo con los valores de la base original', () => {
  for (const nombre of KIT) assert.match(css, new RegExp(`\\.${nombre}\\b`), `falta .${nombre}`)
  for (const sel of ['.btn-primary', '.btn-outline', '.btn-danger', '.btn-danger-outline']) {
    const r = regla(sel)
    assert.match(r, /font-size:\s*14px/, `${sel}: 14 px`)
    assert.match(r, /font-weight:\s*600/, `${sel}: peso 600`)
    assert.match(r, /border-radius:\s*var\(--radius-btn\)/, `${sel}: radio del token`)
    assert.match(r, /padding:\s*12px 24px/, `${sel}: relleno 12px 24px`)
  }
  assert.match(regla('.btn-sm'), /padding:\s*6px 14px/)
  assert.match(regla('.btn-auto'), /width:\s*auto/)
  assert.match(css, /\.btn-danger-outline:focus-visible/, 'foco visible en todas las variantes')
})

test('ningún componente redefine las clases del kit ni conserva los botones retirados', () => {
  const mal = []
  for (const ruta of archivos(raiz)) {
    const css_local = estilos(readFileSync(ruta, 'utf8'))
    const marcado = readFileSync(ruta, 'utf8').replace(/<style[\s\S]*?<\/style>/g, '')
    for (const nombre of KIT) {
      // Se permite refinar un contexto concreto (p. ej. `.lista-versiones .btn-link.activo`), no definir el botón base.
      const base = new RegExp(`(^|[},\\n])\\s*(:global\\()?\\.${nombre}(:[a-z-]+(\\([^)]*\\))?)?\\s*[,{]`, 'm')
      if (base.test(css_local)) mal.push(`${relative(raiz, ruta)}: redefine .${nombre}`)
    }
    for (const nombre of RETIRADOS) {
      if (new RegExp(`\\.${nombre}\\b`).test(css_local) || new RegExp(`class="[^"]*\\b${nombre}\\b`).test(marcado)) {
        mal.push(`${relative(raiz, ruta)}: usa el botón retirado .${nombre}`)
      }
    }
  }
  assert.deepEqual(mal, [])
})

test('los botones de acción de las variantes nuevas cumplen el contraste (hover incluido)', () => {
  // El hover del peligro (#B91C1C) es más oscuro que --error: el texto blanco solo mejora.
  assert.match(css, /\.btn-danger:hover:not\(:disabled\)\s*\{\s*background:\s*#B91C1C/)
})
