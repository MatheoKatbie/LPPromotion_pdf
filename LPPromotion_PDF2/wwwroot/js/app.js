window.getDroppedFiles = function () {
  return new Promise((resolve) => {
    const dropZone = document.querySelector('.upload-area')
    if (!dropZone) return resolve([])

    const handleDrop = (e) => {
      e.preventDefault()
      e.stopPropagation()
      dropZone.classList.remove('dragover')

      const files = Array.from(e.dataTransfer.files)
      resolve(files)

      // Nettoyer les event listeners
      dropZone.removeEventListener('drop', handleDrop)
      dropZone.removeEventListener('dragenter', handleDragEnter)
      dropZone.removeEventListener('dragleave', handleDragLeave)
      dropZone.removeEventListener('dragover', handleDragOver)
    }

    const handleDragEnter = (e) => {
      e.preventDefault()
      e.stopPropagation()
      dropZone.classList.add('dragover')
    }

    const handleDragLeave = (e) => {
      e.preventDefault()
      e.stopPropagation()
      dropZone.classList.remove('dragover')
    }

    const handleDragOver = (e) => {
      e.preventDefault()
      e.stopPropagation()
    }

    dropZone.addEventListener('drop', handleDrop)
    dropZone.addEventListener('dragenter', handleDragEnter)
    dropZone.addEventListener('dragleave', handleDragLeave)
    dropZone.addEventListener('dragover', handleDragOver)
  })
}
