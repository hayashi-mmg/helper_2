import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ShoppingPage from '../ShoppingPage'
import { renderWithProviders, mockHelperUser } from '@/test-utils'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/api/shopping', () => ({
  getShoppingRequests: vi.fn().mockResolvedValue([{
    id: 'sr1', senior_user_id: 'u1', helper_user_id: 'user-2',
    request_date: '2025-07-14', status: 'pending', notes: 'お願いします',
    items: [
      { id: 'si1', item_name: '牛乳', category: '食材', quantity: '1本', status: 'pending', created_at: '2025-01-01' },
      { id: 'si2', item_name: '食パン', category: '食材', quantity: '1袋', status: 'pending', created_at: '2025-01-01' },
    ],
    created_at: '2025-01-01',
  }]),
  createShoppingRequest: vi.fn(),
  updateShoppingItem: vi.fn(),
}))

describe('ShoppingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().setAuth('token', 'refresh', mockHelperUser)
  })

  it('見出しが表示されること', () => {
    renderWithProviders(<ShoppingPage />)
    expect(screen.getByText('買い物管理')).toBeInTheDocument()
  })

  it('新規依頼ボタンが表示されること', () => {
    renderWithProviders(<ShoppingPage />)
    expect(screen.getByRole('button', { name: '新規依頼' })).toBeInTheDocument()
  })

  it('ステータスフィルタボタンが表示されること', () => {
    renderWithProviders(<ShoppingPage />)
    expect(screen.getByRole('button', { name: 'すべて' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '依頼中' })).toBeInTheDocument()
  })

  it('買い物依頼一覧が表示されること', async () => {
    renderWithProviders(<ShoppingPage />)
    await waitFor(() => {
      expect(screen.getByText('牛乳')).toBeInTheDocument()
      expect(screen.getByText('食パン')).toBeInTheDocument()
    })
  })

  it('アイテムの購入済みボタンが表示されること', async () => {
    renderWithProviders(<ShoppingPage />)
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: '購入済み' }).length).toBe(2)
    })
  })

  it('新規依頼フォームが表示できること', async () => {
    renderWithProviders(<ShoppingPage />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: '新規依頼' }))
    expect(screen.getByText('新しい買い物依頼')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('商品名')).toBeInTheDocument()
  })
})
