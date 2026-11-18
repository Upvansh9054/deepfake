/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        shield: {
          dark: '#0B0F17',
          card: '#111827',
          border: '#1F2937',
          cyan: '#06B6D4',
          danger: '#EF4444',
          warning: '#F59E0B',
          success: '#10B981',
        }
      }
    },
  },
  plugins: [],
}

