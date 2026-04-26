import { createSystem, defaultConfig, defineConfig, mergeConfigs } from '@chakra-ui/react'
import type { ThemeDefinition } from '@/types/theme'

/**
 * ThemeDefinition を Chakra UI v3 の system に変換する。
 * 仕様: docs/theme_system_specification.md §8、docs/frontend_implementation_plan.md §3.1.0
 */
export function buildSystem(definition: ThemeDefinition): ReturnType<typeof createSystem> {
  const brand = Object.fromEntries(
    Object.entries(definition.colors.brand).map(([k, v]) => [k, { value: v }]),
  )
  const neutral = Object.fromEntries(
    Object.entries(definition.colors.neutral).map(([k, v]) => [k, { value: v }]),
  )
  const semantic = Object.fromEntries(
    Object.entries(definition.colors.semantic).map(([k, v]) => [k, { value: v }]),
  )

  const tokens: Record<string, unknown> = {
    colors: {
      brand,
      neutral,
      ...semantic,
    },
    fonts: {
      body: { value: definition.fonts.body },
      heading: { value: definition.fonts.heading },
      ...(definition.fonts.mono ? { mono: { value: definition.fonts.mono } } : {}),
    },
    radii: {
      ...(definition.radii.sm ? { sm: { value: definition.radii.sm } } : {}),
      ...(definition.radii.md ? { md: { value: definition.radii.md } } : {}),
      ...(definition.radii.lg ? { lg: { value: definition.radii.lg } } : {}),
      ...(definition.radii.full ? { full: { value: definition.radii.full } } : {}),
    },
  }

  const semanticTokens = definition.semanticTokens
    ? {
        colors: Object.fromEntries(
          Object.entries(definition.semanticTokens).map(([k, v]) => [k, { value: v }]),
        ),
      }
    : undefined

  const customConfig = defineConfig({
    globalCss: {
      'html, body': {
        fontFamily: definition.fonts.body,
        fontSize: `${definition.fonts.baseSizePx}px`,
        lineHeight: 1.7,
      },
      '*:focus-visible': {
        outline: `3px solid ${resolveRef(definition, definition.semanticTokens?.['border.focus'] ?? '#38BDF8')}`,
        outlineOffset: '2px',
      },
    },
    theme: {
      tokens,
      ...(semanticTokens ? { semanticTokens } : {}),
    },
  })

  return createSystem(mergeConfigs(defaultConfig, customConfig))
}

/**
 * `{colors.brand.500}` 形式のトークン参照を実値に解決する。
 * 直接 hex 値の場合はそのまま返す。解決できない場合は入力値を返す(UI 層で対処)。
 */
function resolveRef(definition: ThemeDefinition, ref: string | undefined): string {
  if (!ref) return '#000000'
  if (ref.startsWith('#')) return ref
  const m = ref.match(/^\{colors\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\}$/)
  if (!m) return ref
  const [, palette, shade] = m
  const paletteObj = (definition.colors as unknown as Record<string, unknown>)[palette]
  if (paletteObj && typeof paletteObj === 'object') {
    const value = (paletteObj as Record<string, string>)[shade]
    if (typeof value === 'string' && value.startsWith('#')) return value
  }
  return ref
}
