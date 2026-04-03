import { Box, Text } from '@chakra-ui/react'
import type { ReactNode } from 'react'

interface FormFieldProps {
  label: string
  required?: boolean
  children: ReactNode
}

export default function FormField({ label, required, children }: FormFieldProps) {
  return (
    <Box>
      <Text fontSize="md" fontWeight="semibold" color="text.primary" mb={1.5}>
        {label}
        {required && <Text as="span" color="danger.500" ml={1}>*</Text>}
      </Text>
      {children}
    </Box>
  )
}
