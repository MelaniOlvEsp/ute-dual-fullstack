import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

// C12 (H4 y estructura): comprobación estática de los .svelte. Cada <select> y cada campo sin <label> necesita un
// nombre accesible, y cada página (presentation/pages) debe declarar una región <main> y un encabezado de primer
// nivel (propio, con el componente PageHeader o con un <h1 class="sr-only">). La medición real con axe-core está en
// tools/auditoria-ui.js; esta prueba evita que se reintroduzcan los casos que ya se corrigieron.
const raiz = join(dirname(fileURLToPath(import.meta.url)), '..', 'src', 'presentation')

function archivos(dir) {
  return readdirSync(dir).flatMap((n) => {
    const ruta = join(dir, n)
    return statSync(ruta).isDirectory() ? archivos(ruta) : ruta.endsWith('.svelte') ? [ruta] : []
  })
}

function etiquetas(texto, nombre) {
  return [...texto.matchAll(new RegExp(`<${nombre}\\b[^>]*>`, 'gs'))].map((m) => m[0])
}

test('cada <select> tiene aria-label o un <label for> asociado', () => {
  for (const ruta of archivos(raiz)) {
    const texto = readFileSync(ruta, 'utf8')
    for (const sel of etiquetas(texto, 'select')) {
      const id = (sel.match(/\bid="([^"]+)"/) || [])[1]
      const conNombre = /aria-label(ledby)?=/.test(sel) || (id && new RegExp(`<label[^>]*\\bfor="${id}"`).test(texto))
      assert.ok(conNombre, `${ruta}: <select${id ? ' id=' + id : ''}> sin nombre accesible`)
    }
  }
})

test('se revisan todas las páginas, también las de sesión, registro y cambio de contraseña', () => {
  const nombres = archivos(join(raiz, 'pages')).map((r) => r.slice(raiz.length + 1).replaceAll('\\', '/'))
  for (const esperada of ['pages/auth/Login.svelte', 'pages/auth/Register.svelte', 'pages/auth/CambiarPassword.svelte',
    'pages/foro/Foro.svelte', 'pages/dual/ReportesDual.svelte', 'pages/dual/CoordinadorDual.svelte']) {
    assert.ok(nombres.includes(esperada), `La prueba no encuentra ${esperada}`)
  }
})

test('cada página declara <main> y un encabezado de primer nivel', () => {
  // Todas las páginas de pages/ se revisan (sin excepciones por usar o no <Navbar>): una pantalla nueva sin <main> falla.
  for (const ruta of archivos(join(raiz, 'pages'))) {
    const texto = readFileSync(ruta, 'utf8')
    const nombre = ruta.slice(raiz.length + 1)
    assert.ok(/<main\b/.test(texto), `${nombre}: falta <main>`)
    assert.ok(/<h1\b/.test(texto) || /<PageHeader\b/.test(texto), `${nombre}: falta <h1> o <PageHeader>`)
  }
})
