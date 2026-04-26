import type { ThemeDefinition } from '@/types/theme'

export const highContrastPreset: ThemeDefinition = {
  schema_version: '1.0',
  id: 'high-contrast',
  name: 'ハイコントラスト',
  description: '弱視・高齢者向け。黒白主体の強コントラスト。',
  colors: {
    brand: {
      '50': '#f5f5f5', '100': '#e0e0e0', '200': '#bdbdbd', '300': '#9e9e9e',
      '400': '#616161', '500': '#000000', '600': '#000000', '700': '#000000',
      '800': '#000000', '900': '#000000',
    },
    semantic: { success: '#0d4d10', danger: '#8b0000', warn: '#8b3900', info: '#003d6b' },
    neutral: {
      '50': '#ffffff', '100': '#f5f5f5', '200': '#eeeeee', '300': '#bdbdbd',
      '400': '#757575', '500': '#424242', '600': '#212121', '700': '#121212',
      '800': '#000000', '900': '#000000',
    },
  },
  semanticTokens: {
    'bg.page': '#ffffff',
    'bg.card': '#ffffff',
    'bg.subtle': '{colors.neutral.100}',
    'text.primary': '#000000',
    'text.secondary': '{colors.neutral.600}',
    'text.onBrand': '#ffffff',
    'border.default': '{colors.neutral.500}',
    'border.focus': '#000000',
  },
  fonts: {
    body: "'Noto Sans JP', 'Hiragino Sans', 'Yu Gothic', sans-serif",
    heading: "'Noto Sans JP', 'Hiragino Sans', 'Yu Gothic', sans-serif",
    baseSizePx: 20,
  },
  radii: { sm: '0.125rem', md: '0.25rem', lg: '0.5rem', full: '9999px' },
  density: 'spacious',
  meta: { tags: ['builtin', 'accessibility'] },
}
