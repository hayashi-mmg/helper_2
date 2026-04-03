import client from './client'
import type { Message } from '@/types'

interface MessageListResponse {
  messages: Message[]
  pagination: { limit: number; offset: number; total: number; has_more: boolean }
}

export async function getMessages(params?: {
  partner_id?: string
  limit?: number
  offset?: number
}): Promise<MessageListResponse> {
  const { data } = await client.get<MessageListResponse>('/messages', { params })
  return data
}

export async function sendMessage(params: {
  receiver_id: string
  content: string
  message_type?: string
}): Promise<Message> {
  const { data } = await client.post<Message>('/messages', params)
  return data
}

export async function markAsRead(id: string): Promise<void> {
  await client.put(`/messages/${id}/read`)
}
