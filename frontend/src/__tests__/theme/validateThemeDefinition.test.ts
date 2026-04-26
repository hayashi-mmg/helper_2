import { describe, expect, it } from 'vitest'
import { contrastRatio, validateThemeDefinition } from '@/theme/validateThemeDefinition'
import { standardPreset } from '@/theme/presets/standard'

describe('contrastRatio', () => {
  it('white vs black = 21.0', () => {
    expect(contrastRatio('#ffffff', '#000000')).toBeCloseTo(21.0, 1)
  })

  it('same color = 1.0', () => {
    expect(contrastRatio('#1976d2', '#1976d2')).toBeCloseTo(1.0, 2)
  })

  it('#212121 vs white ≈ 16.1', () => {
    expect(contrastRatio('#212121', '#ffffff')).toBeCloseTo(16.1, 0)
  })
})

describe('validateThemeDefinition', () => {
  it('accepts standard preset', () => {
    const result = validateThemeDefinition(standardPreset as unknown as Record<string, unknown>)
    expect(result.ok).toBe(true)
  })

  it('rejects baseSizePx < 18', () => {
    const bad = structuredClone(standardPreset) as unknown as Record<string, unknown>
    ;(bad.fonts as { baseSizePx: number }).baseSizePx = 17
    const result = validateThemeDefinition(bad)
    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.errors.some((e) => e.code === 'font_size_too_small')).toBe(true)
    }
  })

  it('rejects low text contrast', () => {
    const bad = structuredClone(standardPreset) as unknown as Record<string, unknown>
    ;(bad.semanticTokens as Record<string, string>)['text.primary'] = '#bbbbbb'
    const result = validateThemeDefinition(bad)
    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.errors.some((e) => e.code === 'text_bg_contrast_too_low')).toBe(true)
    }
  })

  it('rejects invalid schema_version', () => {
    const bad = structuredClone(standardPreset) as unknown as Record<string, unknown>
    bad.schema_version = '2.0'
    const result = validateThemeDefinition(bad)
    expect(result.ok).toBe(false)
  })

  it('rejects unresolved token reference', () => {
    const bad = structuredClone(standardPreset) as unknown as Record<string, unknown>
    ;(bad.semanticTokens as Record<string, string>)['text.primary'] = '{colors.nonexistent.500}'
    const result = validateThemeDefinition(bad)
    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.errors.some((e) => e.code === 'unresolved_token_reference')).toBe(true)
    }
  })
})
