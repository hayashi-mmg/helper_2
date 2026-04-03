import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import PantryPage from '../PantryPage'
import { renderWithProviders, mockSeniorUser } from '@/test-utils'
import { useAuthStore } from '@/stores/auth'

const mockGetPantryItems = vi.fn()
const mockUpdatePantryItems = vi.fn()
const mockDeletePantryItem = vi.fn()

vi.mock('@/api/pantry', () => ({
  getPantryItems: (...args: unknown[]) => mockGetPantryItems(...args),
  updatePantryItems: (...args: unknown[]) => mockUpdatePantryItems(...args),
  deletePantryItem: (...args: unknown[]) => mockDeletePantryItem(...args),
}))

const emptyPantry = { pantry_items: [], total: 0 }
const samplePantry = {
  pantry_items: [
    { id: 'p1', name: 'しょうゆ', category: '調味料', is_available: true, updated_at: '2025-07-13T00:00:00Z' },
    { id: 'p2', name: 'みりん', category: '調味料', is_available: true, updated_at: '2025-07-13T00:00:00Z' },
    { id: 'p3', name: '米', category: '穀類', is_available: false, updated_at: '2025-07-13T00:00:00Z' },
  ],
  total: 3,
}

describe('PantryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().setAuth('token', 'refresh', mockSeniorUser)
    mockGetPantryItems.mockResolvedValue(samplePantry)
  })

  it('見出しが表示されること', () => {
    renderWithProviders(<PantryPage />)
    expect(screen.getByText('パントリー（在庫管理）')).toBeInTheDocument()
  })

  it('パントリーアイテムが表示されること', async () => {
    renderWithProviders(<PantryPage />)
    await waitFor(() => {
      expect(screen.getByText('しょうゆ')).toBeInTheDocument()
      expect(screen.getByText('みりん')).toBeInTheDocument()
      expect(screen.getByText('米')).toBeInTheDocument()
    })
  })

  it('空の場合にEmptyStateが表示されること', async () => {
    mockGetPantryItems.mockResolvedValue(emptyPantry)
    renderWithProviders(<PantryPage />)
    await waitFor(() => {
      expect(screen.getByText('パントリーに食材が登録されていません')).toBeInTheDocument()
    })
  })

  it('食材追加ボタンが表示されること', () => {
    renderWithProviders(<PantryPage />)
    expect(screen.getByText('+ 食材を追加')).toBeInTheDocument()
  })

  it('在庫あり/なしのトグルボタンが表示されること', async () => {
    renderWithProviders(<PantryPage />)
    await waitFor(() => {
      const availableButtons = screen.getAllByText('在庫あり')
      expect(availableButtons.length).toBe(2)
      expect(screen.getByText('在庫なし')).toBeInTheDocument()
    })
  })

  it('サマリーが正しく表示されること', async () => {
    renderWithProviders(<PantryPage />)
    await waitFor(() => {
      expect(screen.getByText('全3件')).toBeInTheDocument()
      expect(screen.getByText('在庫あり: 2件')).toBeInTheDocument()
    })
  })
})
