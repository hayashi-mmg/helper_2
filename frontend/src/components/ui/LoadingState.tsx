import { Box, VStack, Skeleton, SkeletonText } from '@chakra-ui/react'

interface LoadingStateProps {
  type?: 'cards' | 'list' | 'form'
  count?: number
}

export default function LoadingState({ type = 'cards', count = 3 }: LoadingStateProps) {
  if (type === 'list') {
    return (
      <VStack gap={4} align="stretch">
        {Array.from({ length: count }).map((_, i) => (
          <Box key={i} bg="bg.card" p={6} borderRadius="xl" border="1px solid" borderColor="border.default">
            <Skeleton height="20px" width="60%" mb={3} />
            <SkeletonText noOfLines={2} />
          </Box>
        ))}
      </VStack>
    )
  }

  if (type === 'form') {
    return (
      <Box bg="bg.card" p={6} borderRadius="xl" border="1px solid" borderColor="border.default">
        <Skeleton height="24px" width="40%" mb={4} />
        <VStack gap={4} align="stretch">
          {Array.from({ length: count }).map((_, i) => (
            <Skeleton key={i} height="44px" borderRadius="lg" />
          ))}
        </VStack>
      </Box>
    )
  }

  return (
    <Box display="grid" gridTemplateColumns="repeat(auto-fill, minmax(280px, 1fr))" gap={6}>
      {Array.from({ length: count }).map((_, i) => (
        <Box key={i} bg="bg.card" p={6} borderRadius="xl" border="1px solid" borderColor="border.default">
          <Skeleton height="20px" width="70%" mb={3} />
          <SkeletonText noOfLines={3} />
        </Box>
      ))}
    </Box>
  )
}
