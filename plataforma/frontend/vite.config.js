import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Despliegue integrado — Fase 4 (corte final):
//
// React es la interfaz principal en "/". nginx sirve el build estático en
// la raíz y reenvía /api/, /login/, /rbac/, /riesgos/, etc. a cada backend.
//
// El proxy de desarrollo imita el mismo enrutamiento que nginx en producción
// (sección 3.2 del README): /api -> Inventario (Django), /rbac -> Matriz RBAC
// (Flask). Así "npm run dev" habla con los backends reales sin CORS.
export default defineConfig({
  base: '/',
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
