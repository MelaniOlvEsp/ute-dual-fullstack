import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

// C11 (H2): los tokens de color de global.css cumplen el contraste mínimo de WCAG 1.4.3 (4.5:1 para texto normal)
// en el tema claro y en el oscuro. Es una comprobación de los tokens; el contraste real de cada pantalla se mide con
// tools/auditoria-ui.js (axe-core) en el navegador.
const css = readFileSync(join(dirname(fileURLToPath(import.meta.url)), '..', 'src', 'global.css'), 'utf8')

function bloque(selector) {
  const inicio = css.indexOf(selector + ' {')
  assert.ok(inicio >= 0, `No se encontró ${selector}`)
  return css.slice(inicio, css.indexOf('}', inicio))
}

function tokens(texto) {
  return Object.fromEntries([...texto.matchAll(/--([a-z-]+):\s*(#[0-9A-Fa-f]{6})/g)].map((m) => [m[1], m[2]]))
}

const claro = tokens(bloque(':root'))
const oscuro = { ...claro, ...tokens(bloque('[data-theme="dark"]')) }

function luminancia(hex) {
  const canal = (i) => {
    const v = parseInt(hex.slice(1 + i * 2, 3 + i * 2), 16) / 255
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
  }
  return 0.2126 * canal(0) + 0.7152 * canal(1) + 0.0722 * canal(2)
}

function contraste(a, b) {
  const [x, y] = [luminancia(a), luminancia(b)].sort((p, q) => q - p)
  return (x + 0.05) / (y + 0.05)
}

const BLANCO = '#FFFFFF'
const PARES = [
  ['text-primary', 'bg-card'], ['text-secondary', 'bg-card'], ['text-disabled', 'bg-card'], ['text-disabled', 'bg-page'],
  ['text-secondary', 'orange-light'], ['text-disabled', 'orange-light'], ['text-primary', 'orange-light'],
  ['orange', 'bg-card'], ['orange', 'orange-light'], ['error-text', 'bg-card'], ['success-text', 'bg-card']
]

for (const [nombre, t] of [['claro', claro], ['oscuro', oscuro]]) {
  test(`tema ${nombre}: texto sobre fondo >= 4.5:1`, () => {
    for (const [fg, bg] of PARES) {
      const razon = contraste(t[fg], t[bg])
      assert.ok(razon >= 4.5, `${fg} (${t[fg]}) sobre ${bg} (${t[bg]}): ${razon.toFixed(2)}:1`)
    }
  })
  test(`tema ${nombre}: texto blanco sobre fondos de acción >= 4.5:1`, () => {
    for (const fondo of ['orange-action', 'orange-action-hover', 'error', 'success']) {
      const razon = contraste(BLANCO, t[fondo])
      assert.ok(razon >= 4.5, `blanco sobre ${fondo} (${t[fondo]}): ${razon.toFixed(2)}:1`)
    }
  })
}

test('el naranja de la marca queda como acento: ningún texto usa #F97316', () => {
  assert.ok(!/(^|[\s;{])color:\s*#F97316/i.test(css), 'global.css no debe usar #F97316 como color de texto')
})
