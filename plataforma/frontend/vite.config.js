import path from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// Defaults de la SPA unificada — un `npm run build` sin ENV no debe dejar
// Riesgos apuntando a localhost:8000 (bug real en despliegues con Docker).
process.env.VITE_PLATAFORMA_UNIFICADA ??= '1';
process.env.VITE_API_BASE_URL ??= '/riesgos/api';
process.env.VITE_INVENTARIO_BASE_URL ??= '/api';

const raiz = path.resolve(__dirname);
const depsCompartidas = ['react', 'react-dom', 'react-router-dom', 'axios', 'lucide-react', 'recharts'];
const aliasDeps = Object.fromEntries(
  depsCompartidas.map((dep) => [dep, path.join(raiz, 'node_modules', dep)]),
);

// React es la interfaz principal en "/". nginx reenvía /api/, /rbac/api/,
// /riesgos/api/, etc. a cada backend.
export default defineConfig({
  base: '/',
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@riesgos': path.resolve(raiz, '../riesgos/frontend/src'),
      ...aliasDeps,
    },
    dedupe: depsCompartidas,
  },
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/rbac': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/rbac/, ''),
      },
      '/riesgos/api': { target: 'http://localhost:8001', changeOrigin: true, rewrite: (p) => p.replace(/^\/riesgos/, '') },
      '/riesgos/media': { target: 'http://localhost:8001', changeOrigin: true, rewrite: (p) => p.replace(/^\/riesgos/, '') },
    },
  },
  build: {
    outDir: 'dist',
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/pruebas/setup.js',
    globals: true,
  },
});
