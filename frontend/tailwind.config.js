/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0a0f0d',
        header: '#0e1411',
        surface: '#111915',
        'surface-2': '#17211c',
        line: '#1f2b25',
        'line-strong': '#2a3831',
        ink: '#e7ede9',
        muted: '#8a978f',
        dim: '#56635c',
        accent: { DEFAULT: '#34d98c', deep: '#1f9360', soft: '#11281d' },
        warn: { DEFAULT: '#e9b44c', soft: '#2e2412' },
        info: { DEFAULT: '#6fa8ea', soft: '#152235' },
        danger: { DEFAULT: '#e5564d', soft: '#2c1413' },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}
