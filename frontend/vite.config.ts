import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import compression from 'vite-plugin-compression'
import path from 'path'

export default defineConfig({
  plugins: [
    react(),
    compression({ algorithm: 'gzip', ext: '.gz', threshold: 1024, compressionOptions: { level: 9 } }),
    compression({ algorithm: 'brotliCompress', ext: '.br', threshold: 1024, compressionOptions: { level: 11 } }),
  ],
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:18443',
    },
  },
})