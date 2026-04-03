import { Box, Text, VStack } from '@chakra-ui/react'

interface EmptyStateProps {
  message: string
  icon?: string
}

export default function EmptyState({ message, icon = 'inbox' }: EmptyStateProps) {
  const icons: Record<string, string> = {
    inbox: 'M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4',
    search: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z',
    calendar: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z',
    cart: 'M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z',
  }

  return (
    <Box
      py={16}
      bg="bg.card"
      borderRadius="xl"
      border="1px solid"
      borderColor="border.default"
      textAlign="center"
    >
      <VStack gap={4}>
        <svg
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#94A3B8"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d={icons[icon] || icons.inbox} />
        </svg>
        <Text fontSize="lg" color="text.muted">
          {message}
        </Text>
      </VStack>
    </Box>
  )
}
