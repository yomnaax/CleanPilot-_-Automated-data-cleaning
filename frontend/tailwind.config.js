/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        cp: {
          bg: '#0a0a0f',
          surface: '#111118',
          card: '#16161f',
          border: '#2a2a3a',
          purple: '#7c5cfc',
          'purple-light': '#9d84fd',
          'purple-dim': '#3d2e7a',
          blue: '#4a9eff',
          cyan: '#00d4d8',
          text: '#e8e8f0',
          muted: '#8888aa',
          faint: '#444460',
        }
      },
      fontFamily: {
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.4s ease forwards',
        'slide-up': 'slideUp 0.4s ease forwards',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp: { from: { opacity: 0, transform: 'translateY(16px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        pulseSoft: { '0%,100%': { opacity: 1 }, '50%': { opacity: 0.5 } },
      }
    }
  },
  plugins: []
}
