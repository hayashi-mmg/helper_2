import type { ThemeDefinition } from '@/types/theme'

export const warmPreset: ThemeDefinition = {
  schema_version: '1.0',
  id: 'warm',
  name: '温もり',
  description: '居宅介護の温かみを表現する橙系テーマ。',
  colors: {
    brand: {
      '50': '#fff3e0', '100': '#ffe0b2', '200': '#ffcc80', '300': '#ffb74d',
      '400': '#ffa726', '500': '#b84d00', '600': '#a14300', '700': '#8a3a00',
      '800': '#732f00', '900': '#5a2500',
    },
    semantic: { success: '#2e7d32', danger: '#b71c1c', warn: '#b84d00', info: '#01579b' },
    neutral: {
      '50': '#fffaf4', '100': '#fdf3e5', '200': '#f3e3cc', '300': '#e5d0b0',
      '400': '#b89773', '500': '#7a624a', '600': '#5e4a36', '700': '#3f3322',
      '800': '#2b2116', '900': '#1a140c',
    },
  },
  semanticTokens: {
    'bg.page': '{colors.neutral.50}',
    'bg.card': '#ffffff',
    'bg.subtle': '{colors.neutral.100}',
    'text.primary': '{colors.neutral.800}',
    'text.secondary': '{colors.neutral.700}',
    'text.onBrand': '#ffffff',
    'border.default': '{colors.neutral.300}',
    'border.focus': '{colors.brand.700}',
  },
  fonts: {
    body: "'Noto Sans JP', 'Hiragino Sans', 'Yu Gothic', sans-serif",
    heading: "'Noto Sans JP', 'Hiragino Sans', 'Yu Gothic', sans-serif",
    baseSizePx: 18,
  },
  radii: { sm: '0.375rem', md: '0.75rem', lg: '1rem', full: '9999px' },
  density: 'comfortable',
  meta: { tags: ['builtin', 'warm'] },
}
