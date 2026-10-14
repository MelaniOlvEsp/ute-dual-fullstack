// Adaptador HTTP de identidad y recuperaciones institucionales.
export function createAuthRepository(http) {
  return {
    register: body => http.post('/auth/register', body),
    login: body => http.post('/auth/login', body),
    me: () => http.get('/auth/me'),
    studentProfile: () => http.get('/auth/me'),
    crearTutor: body => http.post('/auth/tutores', body),
    listarTutores: () => http.get('/auth/tutores'),
    eliminarTutor: id => http.delete(`/auth/tutores/${encodeURIComponent(id)}`),
    passwordProvisional: matricula => http.post(`/auth/alumnos/${encodeURIComponent(matricula)}/password-provisional`, {}),
    cambiarPassword: body => http.post('/auth/cambiar-password', body)
  }
}
