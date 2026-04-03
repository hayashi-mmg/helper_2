import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Box, Text, VStack, Input, Button, HStack, Flex } from '@chakra-ui/react'
import { getMessages, sendMessage } from '@/api/messages'
import { useAuthStore } from '@/stores/auth'
import PageHeader from '@/components/ui/PageHeader'
import FormField from '@/components/ui/FormField'
import LoadingState from '@/components/ui/LoadingState'
import EmptyState from '@/components/ui/EmptyState'

export default function MessagesPage() {
  const [content, setContent] = useState('')
  const [partnerId, setPartnerId] = useState('')
  const user = useAuthStore((state) => state.user)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['messages', partnerId],
    queryFn: () => getMessages({ partner_id: partnerId || undefined }),
  })

  const mutation = useMutation({
    mutationFn: (params: { receiver_id: string; content: string }) => sendMessage(params),
    onSuccess: () => {
      setContent('')
      queryClient.invalidateQueries({ queryKey: ['messages'] })
    },
  })

  const handleSend = () => {
    if (!content.trim() || !partnerId) return
    mutation.mutate({ receiver_id: partnerId, content })
  }

  return (
    <Box>
      <PageHeader title="メッセージ" />

      <Box mb={6}>
        <FormField label="相手のユーザーID">
          <Input
            placeholder="ユーザーIDを入力"
            value={partnerId}
            onChange={(e) => setPartnerId(e.target.value)}
            size="lg"
            borderRadius="lg"
            maxW="500px"
            bg="bg.card"
          />
        </FormField>
      </Box>

      <Box
        bg="bg.card"
        borderRadius="xl"
        border="1px solid"
        borderColor="border.default"
        overflow="hidden"
      >
        {/* Message Area */}
        <Box p={6} minH="400px" maxH="600px" overflowY="auto">
          {isLoading ? (
            <LoadingState type="list" count={3} />
          ) : !data?.messages.length ? (
            <EmptyState message="メッセージはありません" />
          ) : (
            <VStack gap={3} align="stretch">
              {data.messages.map((msg) => {
                const isMine = msg.sender_id === user?.id
                return (
                  <Flex key={msg.id} justify={isMine ? 'flex-end' : 'flex-start'}>
                    <Box
                      bg={isMine ? 'brand.600' : 'bg.muted'}
                      color={isMine ? 'white' : 'text.primary'}
                      px={4}
                      py={3}
                      borderRadius="2xl"
                      borderBottomRightRadius={isMine ? 'sm' : '2xl'}
                      borderBottomLeftRadius={isMine ? '2xl' : 'sm'}
                      maxW="70%"
                    >
                      <Text fontSize="md">{msg.content}</Text>
                      <Text
                        fontSize="xs"
                        mt={1}
                        opacity={0.7}
                        color={isMine ? 'whiteAlpha.800' : 'text.muted'}
                      >
                        {new Date(msg.created_at).toLocaleString('ja-JP')}
                      </Text>
                    </Box>
                  </Flex>
                )
              })}
            </VStack>
          )}
        </Box>

        {/* Input Area */}
        <Box borderTop="1px solid" borderColor="border.default" p={4} bg="bg.muted">
          <HStack gap={3}>
            <Input
              placeholder="メッセージを入力..."
              value={content}
              onChange={(e) => setContent(e.target.value)}
              size="lg"
              borderRadius="xl"
              bg="bg.card"
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            />
            <Button
              bg="brand.600"
              color="white"
              _hover={{ bg: 'brand.700' }}
              size="lg"
              borderRadius="xl"
              px={6}
              onClick={handleSend}
              disabled={!content.trim() || !partnerId}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </Button>
          </HStack>
        </Box>
      </Box>
    </Box>
  )
}
