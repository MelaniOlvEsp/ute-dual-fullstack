import Preview from './Preview.svelte'
import '../../../src/global.css'
// No se permite ninguna solicitud a la API o a Drive durante este preview.
window.fetch = () => Promise.reject(new Error('Preview C15: red de API deshabilitada'))
new Preview({ target: document.getElementById('app') })
