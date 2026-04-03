import { Flex, Heading } from '@chakra-ui/react'
import type { ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  children?: ReactNode
}

export default function PageHeader({ title, children }: PageHeaderProps) {
  return (
    <Flex justify="space-between" align="center" mb={6}>
      <Heading size="2xl" color="text.primary" fontWeight="bold">
        {title}
      </Heading>
      {children}
    </Flex>
  )
}
