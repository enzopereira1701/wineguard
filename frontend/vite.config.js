import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Plugins: React (JSX) e Tailwind CSS v4 (sem arquivo tailwind.config).
export default defineConfig({
  plugins: [react(), tailwindcss()],
})
