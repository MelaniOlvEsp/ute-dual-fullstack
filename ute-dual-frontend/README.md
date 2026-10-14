# Frontend Formación Dual

Svelte 4 + Vite. Arranque canónico desde la raíz con Docker: [guía](../README_INTEGRACION.md).

```powershell
docker.exe compose up --build -d --wait
docker.exe compose exec web npm test
docker.exe compose exec web npm run build
```

Abrir http://127.0.0.1:5174/login. VITE_API_URL se configura con el puerto de API publicado (8001 por defecto), no con el hostname interno api. Compose usa npm ci con package-lock.json existente y conserva servicios de otros proyectos.

Las rutas de la demo permanecen: /login, /register, /cambiar-password, /foro, /dual/reportes, /dual/tutor, /dual/carrera, /dual/accesos y /dual/tutores. C01 no rediseña pantallas ni implementa funcionalidades de incrementos posteriores.

En el host: npm test pasó 20 pruebas; build se generó con 97 módulos y advertencias previas de accesibilidad/CSS. El sandbox Windows requirió una alternativa temporal de resolución realpath; no se añadió ese ajuste al producto ni a Docker.

Ver [evidencia C01](../specs/C01-base-local/evidencia.md) para límites de la validación. Las pruebas de repositorios HTTP usan simulación y no demuestran funcionamiento con PostgreSQL/Drive.
