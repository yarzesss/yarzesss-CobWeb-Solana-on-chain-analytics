import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        cobweb: {
          bg: '#0b0b14',
          'bg-soft': '#0f0f1c',
          surface: '#15152a',
          surface2: '#1f1f3a',
          'surface-hi': '#2a2a4d',
          border: '#34344f',
          'border-soft': '#26263d',
          pink: '#C2185B',
          'pink-light': '#E91E8C',
          'pink-dark': '#880E4F',
          mint: '#4ade80',
          amber: '#fbbf24',
          red: '#ef4444',
          cyan: '#22d3ee',
          muted: '#8888a8',
        },
      },
      fontFamily: {
        pixel: ['var(--font-pixel)', 'monospace'],
        mono: ['var(--font-mono)', 'monospace'],
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        pixel: '4px 4px 0px 0px rgba(194, 24, 91, 0.6)',
        'pixel-sm': '2px 2px 0px 0px rgba(194, 24, 91, 0.5)',
        'pixel-inset': 'inset 2px 2px 0px 0px rgba(0,0,0,0.4)',
        depth: '0 2px 0 0 rgba(0,0,0,0.5), 0 8px 24px -8px rgba(0,0,0,0.6)',
        'depth-hi': '0 0 0 1px rgba(233,30,140,0.25), 0 12px 32px -8px rgba(194,24,91,0.25)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        scanline: 'scanline 8s linear infinite',
        'coby-bob': 'coby-bob 3.2s ease-in-out infinite',
        'coby-thread': 'coby-thread 3.2s ease-in-out infinite',
        'fade-up': 'fade-up 0.4s ease-out both',
      },
      keyframes: {
        scanline: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
        'coby-bob': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(3px)' },
        },
        'coby-thread': {
          '0%, 100%': { transform: 'scaleY(1)' },
          '50%': { transform: 'scaleY(1.06)' },
        },
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
};

export default config;
