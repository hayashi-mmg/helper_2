import { Box, Text, VStack, HStack } from '@chakra-ui/react'
import type { ThemeSummary } from '@/types/theme'

interface Props {
  summary: ThemeSummary
  selected: boolean
  onSelect: () => void
}

/**
 * テーマ選択用のプレビューカード。
 * キーボード操作対応(Space/Enter で選択)、最小タッチターゲット 44px 確保。
 */
export default function ThemeCard({ summary, selected, onSelect }: Props) {
  return (
    <Box
      as="label"
      role="radio"
      aria-checked={selected}
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === ' ' || e.key === 'Enter') {
          e.preventDefault()
          onSelect()
        }
      }}
      cursor="pointer"
      borderWidth="3px"
      borderColor={selected ? 'brand.500' : 'border.default'}
      borderRadius="lg"
      p={4}
      minH="120px"
      minW="220px"
      bg={selected ? 'brand.50' : 'bg.card'}
      _hover={{ borderColor: 'brand.400' }}
      _focusVisible={{ outline: '3px solid', outlineColor: 'brand.500', outlineOffset: '2px' }}
      transition="border-color 0.15s, background-color 0.15s"
    >
      <VStack align="stretch" gap={2}>
        <HStack justify="space-between">
          <Text fontSize="lg" fontWeight="bold">
            {summary.name}
          </Text>
          {summary.is_builtin && (
            <Text fontSize="xs" color="text.secondary" bg="bg.subtle" px={2} py={0.5} borderRadius="sm">
              組込み
            </Text>
          )}
        </HStack>
        {summary.description && (
          <Text fontSize="sm" color="text.secondary">
            {summary.description}
          </Text>
        )}
      </VStack>
    </Box>
  )
}
