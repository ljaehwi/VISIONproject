/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        panel: '#0f1218',
        accent: '#10b981',
        warn: '#ef4444'
      }
    }
  },
  plugins: []
}
