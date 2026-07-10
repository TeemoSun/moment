/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        brand: { 50: '#eef6ff', 100: '#d9ecff', 500: '#007aff', 600: '#0066d6', 700: '#0052ad' },
        ink: { 50: '#f5f5f7', 100: '#e5e5ea', 400: '#8e8e93', 600: '#3a3a3c', 800: '#1d1d1f', 900: '#000000' },
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'SF Pro Display', 'SF Pro Text', 'system-ui', 'sans-serif'],
      },
      borderRadius: { xl: '16px', '2xl': '20px' },
      boxShadow: {
        soft: '0 1px 2px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.05)',
        glass: '0 10px 30px rgba(0,0,0,0.06), 0 2px 6px rgba(0,0,0,0.04)',
      },
      transitionTimingFunction: {
        apple: 'cubic-bezier(0.25, 0.1, 0.25, 1)',
      },
    },
  },
  plugins: [],
}