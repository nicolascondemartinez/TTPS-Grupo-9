import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Tests del frontend (opcionales): npm run test
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/__tests__/setup.js'],
  },
})
