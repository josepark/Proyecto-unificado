import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Despliegue integrado — Fase 2 (migración a React):
//
// `base` queda en "/app/" mientras dura la migración: nginx sigue sirviendo
// la interfaz actual (Django + iframe de RBAC) en "/", y este build de
// React convive aparte en "/app/" para poder probarlo sin arriesgar lo que
// ya funciona. El día del corte final (fin de la Fase 4), esto pasa a "/"
// y nginx.conf se actualiza para servir el build de React como la
// interfaz principal — un solo cambio de una línea en cada lado.
//
// El proxy de desarrollo imita el mismo enrutamiento que nginx usa en
// producción (sección 3.2 del README): /api -> Inventario (Django),
// /rbac -> Matriz RBAC (Flask, que expone su propia API bajo /api/... —
// a través del prefijo queda en /rbac/api/...). Así "npm run dev" habla
// con los backends reales sin problemas de CORS, sin necesitar nginx.
export default defineConfig({
  base: '/app/',
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      // nginx recorta el prefijo "/rbac" antes de reenviar a Flask (su
      // location usa "proxy_pass http://rbac_up/;" con barra final —
      // ver nginx/nginx.conf). El proxy de desarrollo hace lo mismo con
      // `rewrite`, para que Flask reciba las mismas rutas en los dos
      // entornos ("/api/roles", no "/rbac/api/roles").
      '/rbac': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/rbac/, ''),
      },
    },
  },
  build: {
    outDir: 'dist',
  },
  // Fase 4 (README sección 9.5): antes no había ninguna prueba de
  // frontend configurada — solo las 42+102 del backend. jsdom simula un
  // DOM real para que los componentes se puedan montar y probar fuera
  // del navegador; setupFiles registra los matchers de jest-dom (p. ej.
  // toBeInTheDocument) una sola vez para toda la suite.
  test: {
    environment: 'jsdom',
    setupFiles: './src/pruebas/setup.js',
    globals: true,
  },
})
