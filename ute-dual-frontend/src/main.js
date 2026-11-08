import { mount } from 'svelte'
import './global.css';

const response = await fetch('/config.json', { cache: 'no-store' })
if (!response.ok) throw new Error('No se pudo cargar la configuración del portal')
window.__UTE_CONFIG__ = await response.json()
const { default: App } = await import('./App.svelte')
const app = mount(App, {
  target: document.getElementById('app')
})

export default app
