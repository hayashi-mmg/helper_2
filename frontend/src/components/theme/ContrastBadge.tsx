import { Box, HStack, Text } from '@chakra-ui/react'
import { contrastRatio } from '@/theme/validateThemeDefinition'

interface Props {
  label: string
  fg: string
  bg: string
  minRatio: number
}

/**
 * WCAG 2.1 AA コントラスト比をリアルタイム表示するバッジ。
 * 基準未達の場合は赤背景、達成時は緑背景。
 */
export default function ContrastBadge({ label, fg, bg, minRatio }: Props) {
  let ratio: number | null = null
  try {
    ratio = contrastRatio(fg, bg)
  } catch {
    ratio = null
  }

  const passed = ratio !== null && ratio >= minRatio
  const bgColor = ratio === null ? 'gray.200' : passed ? 'green.100' : 'red.100'
  const textColor = ratio === null ? 'gray.700' : passed ? 'green.800' : 'red.800'

  return (
    <HStack gap={3} p={3} bg={bgColor} borderRadius="md" borderWidth="1px" borderColor={textColor}>
      <Box
        w="32px"
        h="32px"
        bg={bg}
        borderRadius="sm"
        borderWidth="1px"
        borderColor="gray.400"
        display="flex"
        alignItems="center"
        justifyContent="center"
      >
        <Text color={fg} fontWeight="bold" fontSize="md">
          A
        </Text>
      </Box>
      <Box>
        <Text fontSize="sm" fontWeight="bold" color={textColor}>
          {label}
        </Text>
        <Text fontSize="xs" color={textColor}>
          {ratio !== null ? `${ratio.toFixed(2)}:1` : '解決不能'}
          {' '}(基準: {minRatio}:1 以上 {passed ? '✓' : '✗'})
        </Text>
      </Box>
    </HStack>
  )
}
