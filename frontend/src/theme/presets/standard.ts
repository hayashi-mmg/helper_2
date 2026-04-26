import type { ThemeDefinition } from '@/types/theme'

export const standardPreset: ThemeDefinition = {
  schema_version: '1.0',
  id: 'standard',
  name: 'スタンダード',
  description: '既定テーマ。青系ブランドで視認性と汎用性を両立。',
  colors: {
    brand: {
      '50': '#e3f2fd', '100': '#bbdefb', '200': '#90caf9', '300': '#64b5f6',
      '400': '#42a5f5', '500': '#1976d2', '600': '#1565c0', '700': '#0d47a1',
      '800': '#0b3d91', '900': '#08306b',
    },
    semantic: { success: '#2e7d32', danger: '#c62828', warn: '#e65100', info: '#0277bd' },
    neutral: {
      '50': '#fafafa', '100': '#f5f5f5', '200': '#eeeeee', '300': '#e0e0e0',
      '400': '#bdbdbd', '500': '#9e9e9e', '600': '#616161', '700': '#424242',
      '800': '#212121', '900': '#000000',
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
  density: 'comfortable',
  meta: { tags: ['builtin', 'default'] },
}
