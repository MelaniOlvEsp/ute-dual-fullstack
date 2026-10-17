/* Auditoría de interfaz del piloto (C10/C11): desborde horizontal, indicador de foco, controles sin etiqueta y
 * accesibilidad con axe-core (contraste, nombres, regiones desplazables). Se pega en la consola del navegador (o con
 * la herramienta de JavaScript del navegador integrado) con una sesión ya iniciada con una cuenta sintética:
 *
 *   await auditarUI({ rutas: ['/foro', '/dual/tutor'], anchos: [320, 375, 768, 1280], temas: ['light', 'dark'] })
 *
 * Una ruta puede ser un texto o { ruta, nombre, preparar }, donde preparar(documento, ventana) es una función
 * asíncrona que lleva la página a un estado (abrir una revisión, un diálogo, otra pestaña) antes de medir; así se
 * cubren también las vistas que no tienen dirección propia.
 *
 * Antes de auditar, pulsa una vez Tab en la página (modalidad de teclado): sin ella el navegador no aplica
 * `:focus-visible` al enfocar por programa y todos los controles saldrían «sin foco».
 * Cada página se carga en un iframe del mismo origen con el ancho indicado y el tema se fija con `data-theme`. No
 * modifica datos, no envía formularios y no sale de la aplicación salvo para cargar axe-core desde cdnjs.
 * Devuelve una fila por página con: desborde (px de la página que exceden el ancho), sinFoco (controles sin
 * indicador visible al enfocarse), sinEtiqueta y axe (violaciones por regla, con ejemplos).
 */
window.auditarUI = async function auditarUI({ rutas, anchos = [375], temas = ['light', 'dark'], espera = 3000 }) {
  const dormir = (ms) => new Promise((r) => setTimeout(r, ms));
  const AXE = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js';
  const filas = [];
  for (const ancho of anchos) {
    for (const tema of temas) {
      for (const entrada of rutas) {
        const ruta = typeof entrada === 'string' ? entrada : entrada.ruta;
        const etiqueta = typeof entrada === 'string' ? entrada : (entrada.nombre || entrada.ruta);
        const marco = document.createElement('iframe');
        marco.style.cssText = `position:fixed;left:0;top:0;width:${ancho}px;height:900px;border:0;z-index:-1`;
        marco.src = ruta;
        document.body.appendChild(marco);
        try {
          await new Promise((r) => { marco.onload = r; });
          await dormir(espera);
          const d = marco.contentDocument, v = marco.contentWindow;
          if (typeof entrada !== 'string' && entrada.preparar) { await entrada.preparar(d, v); await dormir(1500); }
          d.documentElement.setAttribute('data-theme', tema);
          await dormir(2000);   // las transiciones de color del cambio de tema deben terminar antes de medir el contraste
          await new Promise((ok, mal) => {
            const s = d.createElement('script');
            s.src = AXE; s.onload = ok; s.onerror = () => mal(new Error('No se pudo cargar axe-core'));
            d.head.appendChild(s);
          });
          const visible = (e) => {
            const r = e.getBoundingClientRect(), s = v.getComputedStyle(e);
            return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
          };
          const enfocables = [...d.querySelectorAll('a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"])')]
            .filter((e) => visible(e) && !e.disabled);
          const sinFoco = [];
          for (const e of enfocables) {
            const a = v.getComputedStyle(e);
            const antes = a.outlineStyle + a.outlineWidth + a.boxShadow + a.borderColor + a.backgroundColor + a.color;
            e.focus({ preventScroll: true });
            const b = v.getComputedStyle(e);
            const despues = b.outlineStyle + b.outlineWidth + b.boxShadow + b.borderColor + b.backgroundColor + b.color;
            if (d.activeElement !== e || antes === despues) {
              sinFoco.push(`${e.tagName} ${(e.getAttribute('aria-label') || e.textContent || '').trim().slice(0, 24)}`);
            }
            e.blur();
          }
          const sinEtiqueta = [...d.querySelectorAll('button,a[href],input,select,textarea')].filter((e) => visible(e) && !(
            e.getAttribute('aria-label') || e.textContent.trim() || e.getAttribute('title') || (e.labels && e.labels.length) || e.placeholder)).length;
          const informe = await v.axe.run(d, { resultTypes: ['violations'] });
          filas.push({
            ruta: etiqueta, ancho, tema,
            desborde: Math.max(0, d.documentElement.scrollWidth - v.innerWidth),
            enfocables: enfocables.length, sinFoco: sinFoco.slice(0, 5), sinEtiqueta,
            axe: Object.fromEntries(informe.violations.map((x) => [x.id, {
              nodos: x.nodes.length,
              ejemplo: (x.nodes[0].any[0] && x.nodes[0].any[0].message || x.help).slice(0, 110)
            }]))
          });
        } catch (e) {
          filas.push({ ruta, ancho, tema, error: String(e) });
        } finally {
          marco.remove();
        }
      }
    }
  }
  return filas;
};

/* Resumen de una línea por página para leer rápido. */
window.resumenAuditoria = (filas) => filas.map((f) => f.error ? `ERR ${f.ruta} ${f.ancho} ${f.tema} ${f.error}` :
  `${f.ancho} ${f.tema.padEnd(5)} ${f.ruta.padEnd(28)} desborde=${f.desborde} sinFoco=${f.sinFoco.length} sinEtiqueta=${f.sinEtiqueta} axe=` +
  (Object.keys(f.axe).length ? Object.entries(f.axe).map(([k, x]) => `${k}:${x.nodos}`).join(',') : 'ok')).join('\n');
