<script>
  import { onMount } from 'svelte'
  import { api } from '../../../composition/api.js'

  let registrada = false
  let imagen = null
  let error = ''
  let mensaje = ''
  let saving = false

  onMount(async () => {
    try { registrada = (await api.dual.estadoFirma()).registrada }
    catch (e) { error = e.message }
  })

  async function guardar() {
    error = ''
    mensaje = ''
    if (!imagen || !['image/png', 'image/jpeg'].includes(imagen.type) || imagen.size > 1024 * 1024) {
      error = 'Selecciona una imagen PNG o JPEG menor de 1 MB.'
      return
    }
    saving = true
    try {
      const form = new FormData()
      form.append('imagen', imagen)
      await api.dual.subirFirma(form)
      registrada = true
      imagen = null
      mensaje = 'Firma guardada. Se usará en los PDF que apruebes a partir de ahora.'
    } catch (e) { error = e.message }
    finally { saving = false }
  }
</script>
<section style="background:var(--bg-card);padding:18px;border:1px solid var(--border);border-radius:10px;margin:12px 0 24px">
  <h3>Firma del tutor académico</h3>
  <p>{registrada ? 'Tienes una firma registrada. Puedes reemplazarla.' : 'Adjunta tu firma antes de aprobar reportes.'}</p>
  <p style="font-size:12px">La imagen se estampará en la celda de firma de la fila «Tutor académico» del reporte; si el formato no se reconoce, se agrega una hoja de firma con tu nombre y la fecha de revisión. No equivale a una firma electrónica certificada.</p>
  <input aria-label="Imagen de firma" type="file" accept="image/png,image/jpeg" on:change={e => imagen = e.currentTarget.files?.[0] || null} />
  <button class="btn-primary" on:click={guardar} disabled={!imagen || saving}>{saving ? 'Guardando...' : 'Guardar firma'}</button>
  {#if error}<p style="color:var(--error)">{error}</p>{/if}
  {#if mensaje}<p style="color:var(--success)">{mensaje}</p>{/if}
</section>
