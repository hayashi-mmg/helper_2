import { Toaster as ChakraToaster, createToaster, Box, Text, HStack } from '@chakra-ui/react'

export const toaster = createToaster({
  placement: 'top',
  pauseOnPageIdle: true,
})

export function Toaster() {
  return (
    <ChakraToaster toaster={toaster}>
      {(toast) => (
        <Box
          bg={toast.type === 'error' ? 'danger.50' : toast.type === 'success' ? 'success.50' : 'bg.card'}
          border="1px solid"
          borderColor={toast.type === 'error' ? 'danger.100' : toast.type === 'success' ? 'success.100' : 'border.default'}
          borderRadius="xl"
          px={5}
          py={4}
          shadow="lg"
          minW="300px"
        >
          <HStack gap={3}>
            {toast.type === 'success' && (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#16A34A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            )}
            {toast.type === 'error' && (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#DC2626" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
              </svg>
            )}
            <Text fontSize="md" fontWeight="medium" color="text.primary">
              {toast.title?.toString()}
            </Text>
          </HStack>
        </Box>
      )}
    </ChakraToaster>
  )
}
