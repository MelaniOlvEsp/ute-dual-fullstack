// Native dialogs trap keyboard focus; Escape/backdrop close and restore the opener.
export function modalFocus(node, onClose) {
  const opener = document.activeElement
  function cancel(event) { event.preventDefault(); onClose() }
  function backdrop(event) {
    if (event.target !== node) return
    const box = node.getBoundingClientRect()
    if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) onClose()
  }
  node.addEventListener('cancel', cancel)
  node.addEventListener('click', backdrop)
  node.showModal()
  return {
    update(next) { onClose = next },
    destroy() {
      node.removeEventListener('cancel', cancel)
      node.removeEventListener('click', backdrop)
      node.close()
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus()
    }
  }
}
