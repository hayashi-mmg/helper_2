import { createSystem, defaultConfig, defineConfig, mergeConfigs } from '@chakra-ui/react'

const customConfig = defineConfig({
  globalCss: {
    'html, body': {
      fontFamily: '"Noto Sans JP", "Hiragino Kaku Gothic ProN", "Hiragino Sans", Meiryo, sans-serif',
      fontSize: '18px',
      lineHeight: 1.7,
      color: '#0C4A6E',
      bg: '#F0F9FF',
    },
    '*:focus-visible': {
      outline: '3px solid #38BDF8',
      outlineOffset: '2px',
      borderRadius: 'sm',
    },
  },
  theme: {
    tokens: {
      colors: {
        brand: {
          50: { value: '#F0F9FF' },
          100: { value: '#E0F2FE' },
          200: { value: '#BAE6FD' },
          300: { value: '#7DD3FC' },
          400: { value: '#38BDF8' },
          500: { value: '#0EA5E9' },
          600: { value: '#0369A1' },
          700: { value: '#075985' },
          800: { value: '#0C4A6E' },
          900: { value: '#082F49' },
        },
        success: {
          50: { value: '#F0FDF4' },
          100: { value: '#DCFCE7' },
          500: { value: '#22C55E' },
          600: { value: '#16A34A' },
          700: { value: '#15803D' },
        },
        danger: {
          50: { value: '#FEF2F2' },
          100: { value: '#FEE2E2' },
          500: { value: '#EF4444' },
          600: { value: '#DC2626' },
          700: { value: '#B91C1C' },
        },
        warn: {
          50: { value: '#FFFBEB' },
          100: { value: '#FEF3C7' },
          500: { value: '#F59E0B' },
          600: { value: '#D97706' },
        },
      },
      fonts: {
        heading: { value: '"Noto Sans JP", sans-serif' },
        body: { value: '"Noto Sans JP", sans-serif' },
      },
    },
    semanticTokens: {
      colors: {
        'bg.page': { value: '#F0F9FF' },
        'bg.card': { value: '#FFFFFF' },
        'bg.muted': { value: '#F8FAFC' },
        'text.primary': { value: '#0C4A6E' },
        'text.secondary': { value: '#475569' },
        'text.muted': { value: '#64748B' },
        'border.default': { value: '#E2E8F0' },
        'border.hover': { value: '#CBD5E1' },
      },
    },
  },
})

export const system = createSystem(mergeConfigs(defaultConfig, customConfig))
