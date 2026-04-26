import type { ThemeDefinition, ThemeValidationError } from '@/types/theme'

/**
 * クライアント側のテーマ定義チェック。サーバ側の `theme_validator.py` と同ロジックの縮小版。
 * 登録直前の即時フィードバックと、ThemeProvider のロード時フォールバック判定に使用する。
 *
 * サーバ側バリデーションが最終判定であり、ここは必須ではない。
 */
export function validateThemeDefinition(
  definition: Record<string, unknown>,
): { ok: true; parsed: ThemeDefinition } | { ok: false; errors: ThemeValidationError[] } {
  const errors: ThemeValidationError[] = []

  // 基本フィールド
  if (definition.schema_version !== '1.0') {
    errors.push({
      field: 'schema_version',
      code: 'schema_violation',
      message: 'schema_version は "1.0" である必要があります',
    })
  }

  const colors = definition.colors as { brand?: Record<string, string>; neutral?: Record<string, string>; semantic?: Record<string, string> } | undefined
  if (!colors || !colors.brand || !colors.brand['500']) {
    errors.push({
      field: 'colors.brand.500',
      code: 'schema_violation',
      message: 'colors.brand.500 は必須です',
    })
  }

  const fonts = definition.fonts as { baseSizePx?: number } | undefined
  if (!fonts || typeof fonts.baseSizePx !== 'number') {
    errors.push({ field: 'fonts.baseSizePx', code: 'schema_violation', message: 'baseSizePx が必要です' })
  } else if (fonts.baseSizePx < 18) {
    errors.push({
      field: 'fonts.baseSizePx',
      code: 'font_size_too_small',
      message: `本文フォントサイズは 18px 以上である必要があります(現在 ${fonts.baseSizePx}px)`,
    })
  }

  const density = definition.density
  if (density !== 'compact' && density !== 'comfortable' && density !== 'spacious') {
    errors.push({ field: 'density', code: 'schema_violation', message: 'density が不正です' })
  }

  // 各種コントラスト
  const tokens = definition.semanticTokens as Record<string, string> | undefined
  if (tokens) {
    checkContrast(definition, tokens, 'text.primary', 'bg.page', 4.5, 'text_bg_contrast_too_low', errors)
    checkContrast(definition, tokens, 'border.focus', 'bg.page', 3.0, 'border_focus_contrast_too_low', errors)

    const onBrand = tokens['text.onBrand']
    const brand500 = colors?.brand?.['500']
    if (onBrand && brand500) {
      try {
        const a = resolveHex(definition, onBrand)
        const b = resolveHex(definition, brand500)
        const ratio = contrastRatio(a, b)
        if (ratio < 4.5) {
          errors.push({
            field: 'semanticTokens.text.onBrand',
            code: 'on_brand_contrast_too_low',
            message: `text.onBrand と brand.500 のコントラスト比は 4.5:1 以上が必要です(現在 ${ratio.toFixed(2)}:1)`,
          })
        }
      } catch (e) {
        errors.push({
          field: 'semanticTokens.text.onBrand',
          code: 'unresolved_token_reference',
          message: (e as Error).message,
        })
      }
    }
  }

  if (errors.length > 0) return { ok: false, errors }
  return { ok: true, parsed: definition as unknown as ThemeDefinition }
}

function checkContrast(
  definition: Record<string, unknown>,
  tokens: Record<string, string>,
  fgKey: string,
  bgKey: string,
  minRatio: number,
  code: string,
  errors: ThemeValidationError[],
): void {
  const fg = tokens[fgKey]
  const bg = tokens[bgKey]
  if (!fg || !bg) {
    errors.push({
      field: `semanticTokens.${fgKey}`,
      code: 'missing_token',
      message: `semanticTokens.${fgKey} と semanticTokens.${bgKey} は必須です`,
    })
    return
  }
  try {
    const fgHex = resolveHex(definition, fg)
    const bgHex = resolveHex(definition, bg)
    const ratio = contrastRatio(fgHex, bgHex)
    if (ratio < minRatio) {
      errors.push({
        field: `semanticTokens.${fgKey}`,
        code,
        message: `${fgKey} と ${bgKey} のコントラスト比は ${minRatio}:1 以上が必要です(現在 ${ratio.toFixed(2)}:1)`,
      })
    }
  } catch (e) {
    errors.push({
      field: `semanticTokens.${fgKey}`,
      code: 'unresolved_token_reference',
      message: (e as Error).message,
    })
  }
}

function resolveHex(definition: Record<string, unknown>, value: string): string {
  if (/^#[0-9a-fA-F]{6}$/.test(value)) return value.toLowerCase()
  const m = value.match(/^\{colors\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\}$/)
  if (!m) throw new Error(`unresolved_token_reference: ${value}`)
  const [, palette, shade] = m
  const colors = definition.colors as Record<string, Record<string, string>> | undefined
  const resolved = colors?.[palette]?.[shade]
  if (!resolved || !/^#[0-9a-fA-F]{6}$/.test(resolved)) {
    throw new Error(`unresolved_token_reference: ${value}`)
  }
  return resolved.toLowerCase()
}

export function contrastRatio(hexA: string, hexB: string): number {
  const la = relativeLuminance(hexA)
  const lb = relativeLuminance(hexB)
  const [lighter, darker] = la >= lb ? [la, lb] : [lb, la]
  return (lighter + 0.05) / (darker + 0.05)
}

function relativeLuminance(hex: string): number {
  const r = parseInt(hex.slice(1, 3), 16) / 255
  const g = parseInt(hex.slice(3, 5), 16) / 255
  const b = parseInt(hex.slice(5, 7), 16) / 255
  const channel = (c: number): number =>
    c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
}
