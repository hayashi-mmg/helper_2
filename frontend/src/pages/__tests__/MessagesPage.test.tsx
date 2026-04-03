import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import MessagesPage from '../MessagesPage'
import { renderWithProviders, mockHelperUser } from '@/test-utils'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/api/messages', () => ({
  getMessages: vi.fn().mockResolvedValue({
    messages: [
      { id: 'm1', sender_id: 'user-2', receiver_id: 'user-1', content: 'こんにちは', message_type: 'normal', is_read: false, created_at: '2025-07-14T10:00:00' },
      { id: 'm2', sender_id: 'user-1', receiver_id: 'user-2', content: 'よろしくお願いします', message_type: 'normal', is_read: true, created_at: '2025-07-14T10:05:00' },
    ],
    pagination: { limit: 50, offset: 0, total: 2, has_more: false },
  }),
  sendMessage: vi.fn(),
  markAsRead: vi.fn(),
}))

describe('MessagesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().setAuth('token', 'refresh', mockHelperUser)
  })

  it('見出しが表示されること', () => {
    renderWithProviders(<MessagesPage />)
    expect(screen.getByText('メッセージ')).toBeInTheDocument()
  })

  it('パートナーID入力が表示されること', () => {
    renderWithProviders(<MessagesPage />)
    expect(screen.getByPlaceholderText('相手のユーザーIDを入力')).toBeInTheDocument()
  })

  it('メッセージ入力欄が表示されること', () => {
    renderWithProviders(<MessagesPage />)
    expect(screen.getByPlaceholderText('メッセージを入力...')).toBeInTheDocument()
  })

  it('送信ボタンが表示されること', () => {
    renderWithProviders(<MessagesPage />)
    expect(screen.getByRole('button', { name: '送信' })).toBeInTheDocument()
  })

  it('メッセージ一覧が表示されること', async () => {
    renderWithProviders(<MessagesPage />)
    await waitFor(() => {
      expect(screen.getByText('こんにちは')).toBeInTheDocument()
      expect(screen.getByText('よろしくお願いします')).toBeInTheDocument()
    })
  })
})
