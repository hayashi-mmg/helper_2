import { describe, expect, it } from 'vitest'
import { buildSystem } from '@/theme/buildSystem'
import { standardPreset } from '@/theme/presets/standard'

describe('buildSystem', () => {
  it('returns a Chakra system from a ThemeDefinition', () => {
    const system = buildSystem(standardPreset)
    expect(system).toBeDefined()
    // system.tokens が生成されていること
    expect(system.tokens).toBeDefined()
  })

  it('does not throw when semantic tokens reference neutral palette', () => {
    expect(() => buildSystem(standardPreset)).not.toThrow()
  })
})
