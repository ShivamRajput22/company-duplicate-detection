/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          900: '#0f172a',
          800: '#1e293b',
          700: '#334155',
        },
        tealAccent: {
          500: '#0d9488',
          600: '#0f766e',
          400: '#14b8a6',
        }
      }
    },
  },
  plugins: [],
}
