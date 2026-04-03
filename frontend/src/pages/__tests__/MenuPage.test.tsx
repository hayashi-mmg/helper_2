import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import MenuPage from '../MenuPage'
import { renderWithProviders, mockSeniorUser } from '@/test-utils'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/api/menus', () => ({
  getWeeklyMenu: vi.fn().mockResolvedValue({
    week_start: '2025-07-14',
    menus: {
      monday: { breakfast: [], dinner: [] },
      tuesday: { breakfast: [], dinner: [] },
      wednesday: { breakfast: [], dinner: [] },
      thursday: { breakfast: [], dinner: [] },
      friday: { breakfast: [], dinner: [] },
      saturday: { breakfast: [], dinner: [] },
      sunday: { breakfast: [], dinner: [] },
    },
    summary: { total_recipes: 0, avg_cooking_time: 0, category_distribution: {} },
  }),
  updateWeeklyMenu: vi.fn(),
  copyWeeklyMenu: vi.fn(),
  clearWeeklyMenu: vi.fn(),
}))

vi.mock('@/api/recipes', () => ({
  getRecipes: vi.fn().mockResolvedValue({
    recipes: [{ id: 'r1', name: '目玉焼き', category: '和食', type: '主菜', difficulty: '簡単', cooking_time: 5, created_at: '2025-01-01', updated_at: '2025-01-01' }],
    pagination: { page: 1, limit: 100, total: 1, total_pages: 1, has_next: false, has_prev: false },
  }),
}))

describe('MenuPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().setAuth('token', 'refresh', mockSeniorUser)
  })

  it('見出しが表示されること', () => {
    renderWithProviders(<MenuPage />)
    expect(screen.getByText('週間献立')).toBeInTheDocument()
  })

  it('全曜日が表示されること', async () => {
    renderWithProviders(<MenuPage />)
    await waitFor(() => {
      for (const day of ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日']) {
        expect(screen.getByText(day)).toBeInTheDocument()
      }
    })
  })

  it('朝食・夕食のセクションが表示されること', async () => {
    renderWithProviders(<MenuPage />)
    await waitFor(() => {
      expect(screen.getAllByText('朝食').length).toBe(7)
      expect(screen.getAllByText('夕食').length).toBe(7)
    })
  })

  it('週ナビゲーションボタンが表示されること', () => {
    renderWithProviders(<MenuPage />)
    expect(screen.getByRole('button', { name: '前の週' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '次の週' })).toBeInTheDocument()
  })

  it('前週コピーボタンが表示されること', () => {
    renderWithProviders(<MenuPage />)
    expect(screen.getByRole('button', { name: /前週コピー/ })).toBeInTheDocument()
  })

  it('レシピ追加ボタンが各食事スロットに表示されること', async () => {
    renderWithProviders(<MenuPage />)
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /レシピを追加/ }).length).toBe(14)
    })
  })

  it('献立クリアボタンが表示されること', async () => {
    renderWithProviders(<MenuPage />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /クリア/ })).toBeInTheDocument()
    })
  })
})
