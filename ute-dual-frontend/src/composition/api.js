import { get } from 'svelte/store'
import { token, logout } from '../presentation/stores/auth.js'
import { createHttpClient } from '../infrastructure/http/httpClient.js'
import { createFileSaver } from '../infrastructure/http/fileSaver.js'
import { createReportForm } from '../infrastructure/http/reportForm.js'
import { createAuthRepository } from '../infrastructure/repositories/authRepository.js'
import { createForumRepository } from '../infrastructure/repositories/forumRepository.js'
import { createDualRepository } from '../infrastructure/repositories/dualRepository.js'
import { createApplication } from '../application/use-cases/index.js'

const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const http = createHttpClient({
  baseUrl,
  fetcher: (...args) => fetch(...args),
  getToken: () => get(token),
  onUnauthorized: () => {
    logout()
    window.location.replace('/login')
  }
})

// Ensambla implementaciones externas y casos de uso en un solo lugar.
export const api = createApplication({
  auth: createAuthRepository(http),
  forum: createForumRepository(http),
  dual: createDualRepository(http, baseUrl),
  files: createFileSaver(),
  reportForm: createReportForm
})
