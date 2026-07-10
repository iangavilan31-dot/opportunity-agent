/** @type {import('tailwindcss').Config} */
// WEB MACHINE identity — mostly monochrome; red is reserved for meaningful
// business activity (reply / meeting / won / live pulse). Confidence reads as
// brightness, never as hue. No decorative color.
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#060607',
        surface: '#0c0c0e',
        's2': '#111114',
        's3': '#17171a',
        border: '#1c1c20',
        'border-subtle': '#141417',
        primary: '#f5f5f6',
        muted: '#a2a2ab',
        dim: '#62626c',
        accent: '#f5f5f6',
        'accent-dim': '#26262b',
        // confidence = brightness (monochrome bands)
        'score-high': '#f5f5f6',
        'score-mid': '#9b9ba4',
        'score-low': '#5c5c66',
        'score-fail': '#3c3c44',
        // legacy hue keys flattened into the system — red is the ONLY signal
        'green': '#e8e8ea',
        'green-dim': '#1a1a1e',
        'yellow': '#9b9ba4',
        'red': '#e5484d',
        'red-dim': '#2a1214',
        'blue': '#c9c9cf',
        'purple': '#9b9ba4',
        'cyan': '#c9c9cf',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Cascadia Code', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        '2xs': ['10px', '14px'],
        'xs': ['11px', '16px'],
        'sm': ['12px', '18px'],
        'base': ['13px', '20px'],
        'md': ['14px', '20px'],
        'lg': ['15px', '22px'],
        'xl': ['17px', '24px'],
        '2xl': ['20px', '28px'],
        '3xl': ['24px', '32px'],
      },
    },
  },
  plugins: [],
}
