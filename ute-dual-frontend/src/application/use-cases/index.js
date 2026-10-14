import { createAuthUseCases } from './auth.js'
import { createForumUseCases } from './forum.js'
import { createDualUseCases } from './dual.js'

// Expone a la interfaz casos de uso sin conocimiento de HTTP.
export function createApplication({ auth, dual, forum, files, reportForm }) {
  const messages = createForumUseCases(forum)
  return {
    auth: createAuthUseCases(auth),
    alumno: { me: () => auth.studentProfile() },
    dual: createDualUseCases(dual, files, reportForm),
    foro: messages.foro,
    buzon: messages.buzon
  }
}
