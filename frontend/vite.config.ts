import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// `base: './'` produces relative asset URLs so the built bundle works under
// FastAPI's `/app/` StaticFiles mount AND under DSS's dynamic proxy prefix
// (`/code-studios/PROJECT/.../proxy/PORT/app/`) without a rebuild.
//
// The build output goes DIRECTLY into `../backend/dist/` — that folder is
// checked into git, so `git pull` on DSS ships both the source AND the
// pre-built bundle. No `npm` runs inside DSS.
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    outDir: '../backend/dist',
    emptyOutDir: true,
    sourcemap: false,
  },
  server: {
    port: 5173,
    // Local dev: forward /api/* to the FastAPI dev server on 8000.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
