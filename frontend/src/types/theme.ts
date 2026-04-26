export type ThemeDensity = 'compact' | 'comfortable' | 'spacious'

export interface ThemeColorsSemantic {
  success: string
  danger: string
  warn: string
  info: string
}

export interface ThemeColors {
  brand: Record<string, string>
  semantic: ThemeColorsSemantic
  neutral: Record<string, string>
}

export interface ThemeFonts {
  body: string
  heading: string
  mono?: string
  baseSizePx: number
}

export interface ThemeRadii {
  sm?: string
  md?: string
  lg?: string
  full?: string
}

export interface ThemeMeta {
  previewImageUrl?: string
  tags?: string[]
}

export interface ThemeDefinition {
  schema_version: '1.0'
  id: string
  name: string
  description?: string
  author?: string
  colors: ThemeColors
  semanticTokens?: Partial<
    Record<
      | 'bg.page'
      | 'bg.card'
      | 'bg.subtle'
      | 'text.primary'
      | 'text.secondary'
      | 'text.onBrand'
      | 'border.default'
      | 'border.focus',
      string
    >
  >
  fonts: ThemeFonts
  radii: ThemeRadii
  density: ThemeDensity
  meta?: ThemeMeta
}

export interface ThemeRead {
  theme_key: string
  name: string
  description?: string | null
  definition: ThemeDefinition
  is_builtin: boolean
  is_active: boolean
  updated_at: string
}

export interface ThemeSummary {
  theme_key: string
  name: string
  description?: string | null
  is_builtin: boolean
  is_active: boolean
  preview_image_url?: string | null
  updated_at: string
}

export interface ThemeValidationError {
  field: string
  code: string
  message: string
}
