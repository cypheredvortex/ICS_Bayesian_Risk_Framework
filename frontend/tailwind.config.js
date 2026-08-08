/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        // Inter for UI text, JetBrains Mono for technical/numerical values.
        sans: [
          'Inter',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'sans-serif',
        ],
        mono: [
          'JetBrains Mono',
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'Consolas',
          'monospace',
        ],
      },
      boxShadow: {
        card: '0 1px 2px rgba(2, 6, 23, 0.5), 0 8px 24px rgba(2, 6, 23, 0.35)',
        glow: '0 0 0 4px rgba(34, 211, 238, 0.15)',
      },
    },
  },
  plugins: [],
}
