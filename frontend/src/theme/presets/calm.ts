import type { ThemeDefinition } from '@/types/theme'

export const calmPreset: ThemeDefinition = {
  schema_version: '1.0',
  id: 'calm',
  name: 'おだやか',
  description: '長時間閲覧でも疲れにくい低彩度の緑系テーマ。',
  colors: {
    brand: {
      '50': '#eef5ef', '100': '#d3e4d5', '200': '#b5d1b8', '300': '#97be9b',
      '400': '#7fae83', '500': '#356b3a', '600': '#2d5c32', '700': '#254c28',
      '800': '#1c3c1f', '900': '#132c15',
    },
    semantic: { success: '#2e7d32', danger: '#c62828', warn: '#b84d00', info: '#0277bd' },
    neutral: {
      '50': '#f7f8f7', '100': '#eceeec', '200': '#d6dbd7', '300': '#b8c0b9',
      '400': '#8a948b', '500': '#5a655c', '600': '#414a42', '700': '#2e342f',
      '800': '#1d211e', '900': '#0f110f',
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
  radii: { sm: '0.25rem', md: '0.5rem', lg: '0.75rem', full: '9999px' },
  density: 'spacious',
  meta: { tags: ['builtin', 'calm'] },
}
