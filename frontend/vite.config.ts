import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // '' prefix (not the default 'VITE_') so this also loads the plain,
  // non-VITE_ API_KEY/BACKEND_URL vars -- loadEnv runs in vite.config.ts's
  // own Node process, never in browser-shipped code, so reading a
  // non-VITE_-prefixed secret here is safe; Vite would refuse to expose
  // it to client code even if asked to.
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    server: {
      proxy: {
        // Mirrors the production Netlify Function: the browser only ever
        // calls relative /api/... paths and never sees the API key.
        '/api': {
          target: env.BACKEND_URL || 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
          configure: (proxy) => {
            proxy.on('proxyReq', (proxyReq) => {
              proxyReq.setHeader('X-API-Key', env.API_KEY ?? '')
            })
          },
        },
      },
    },
  }
})
