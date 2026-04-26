import { Box, VStack, HStack, Text } from '@chakra-ui/react'
import type { ThemeDefinition } from '@/types/theme'

interface Props {
  definition: ThemeDefinition | null
}

/**
 * 管理者用のテーマ縮小プレビュー。
 * Chakra Provider を入れ子にする実装は複雑なため、
 * 直接 hex 値でスタイリングして簡易プレビューを描画する。
 */
export default function ThemePreview({ definition }: Props) {
  if (!definition) {
    return (
      <Box p={4} bg="gray.100" borderRadius="md">
        <Text color="gray.500">プレビュー不可(定義が不正)</Text>
      </Box>
    )
  }

  const resolve = (v: string | undefined): string => {
    if (!v) return '#000000'
    if (v.startsWith('#')) return v
    const m = v.match(/^\{colors\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\}$/)
    if (!m) return '#000000'
    const [, palette, shade] = m
    const paletteObj = (definition.colors as unknown as Record<string, Record<string, string>>)[palette]
    return paletteObj?.[shade] ?? '#000000'
  }

  const bgPage = resolve(definition.semanticTokens?.['bg.page'])
  const bgCard = resolve(definition.semanticTokens?.['bg.card'])
  const textPrimary = resolve(definition.semanticTokens?.['text.primary'])
  const textSecondary = resolve(definition.semanticTokens?.['text.secondary'])
  const brand500 = definition.colors.brand['500']
  const textOnBrand = resolve(definition.semanticTokens?.['text.onBrand'])
  const borderDefault = resolve(definition.semanticTokens?.['border.default'])
  const borderFocus = resolve(definition.semanticTokens?.['border.focus'])

  return (
    <Box
      bg={bgPage}
      p={4}
      borderRadius="md"
      borderWidth="1px"
      borderColor="gray.300"
      style={{
        fontFamily: definition.fonts.body,
        fontSize: `${definition.fonts.baseSizePx}px`,
      }}
    >
      <VStack align="stretch" gap={3}>
        <Text color={textPrimary} fontWeight="bold" fontSize="lg">
          プレビュー({definition.name})
        </Text>

        <Box bg={bgCard} p={3} borderRadius="md" borderWidth="1px" borderColor={borderDefault}>
          <Text color={textPrimary}>主要テキスト(本文 {definition.fonts.baseSizePx}px)</Text>
          <Text color={textSecondary} fontSize="sm">
            補助テキスト
          </Text>
        </Box>

        <HStack gap={2}>
          <Box
            bg={brand500}
            color={textOnBrand}
            px={4}
            py={2}
            borderRadius="md"
            fontSize="md"
            fontWeight="bold"
            minH="44px"
            display="flex"
            alignItems="center"
          >
            ブランドボタン
          </Box>
          <Box
            bg={bgCard}
            color={textPrimary}
            px={4}
            py={2}
            borderRadius="md"
            borderWidth="2px"
            borderColor={borderFocus}
            fontSize="md"
            minH="44px"
            display="flex"
            alignItems="center"
          >
            枠線ボタン
          </Box>
        </HStack>

        <Box bg={bgCard} p={3} borderRadius="md" borderWidth="2px" borderColor={borderFocus}>
          <Text color={textPrimary} fontSize="sm">
            フォーカス時の枠(border.focus)
          </Text>
        </Box>
      </VStack>
    </Box>
  )
}
