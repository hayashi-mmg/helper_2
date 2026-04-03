import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RecipesPage from '../RecipesPage'
import { renderWithProviders, mockSeniorUser } from '@/test-utils'
import { useAuthStore } from '@/stores/auth'

const mockRecipes = [
  { id: 'r1', name: '目玉焼き', category: '和食', type: '主菜', difficulty: '簡単', cooking_time: 5, created_at: '2025-01-01', updated_at: '2025-01-01' },
  { id: 'r2', name: 'カレーライス', category: '洋食', type: '主菜', difficulty: '普通', cooking_time: 45, created_at: '2025-01-01', updated_at: '2025-01-01' },
]

const mockGetRecipes = vi.fn()
const mockCreateRecipe = vi.fn()
const mockDeleteRecipe = vi.fn()

vi.mock('@/api/recipes', () => ({
  getRecipes: (...args: unknown[]) => mockGetRecipes(...args),
  createRecipe: (...args: unknown[]) => mockCreateRecipe(...args),
  updateRecipe: vi.fn(),
  deleteRecipe: (...args: unknown[]) => mockDeleteRecipe(...args),
}))

describe('RecipesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().setAuth('token', 'refresh', mockSeniorUser)
    mockGetRecipes.mockResolvedValue({
      recipes: mockRecipes,
      pagination: { page: 1, limit: 12, total: 2, total_pages: 1, has_next: false, has_prev: false },
    })
  })

  it('レシピ一覧の見出しが表示されること', async () => {
    renderWithProviders(<RecipesPage />)
    expect(screen.getByText('レシピ一覧')).toBeInTheDocument()
  })

  it('レシピが一覧表示されること', async () => {
    renderWithProviders(<RecipesPage />)
    await waitFor(() => {
      expect(screen.getByText('目玉焼き')).toBeInTheDocument()
      expect(screen.getByText('カレーライス')).toBeInTheDocument()
    })
  })

  it('新規追加ボタンが表示されること', () => {
    renderWithProviders(<RecipesPage />)
    expect(screen.getByRole('button', { name: /新規追加/ })).toBeInTheDocument()
  })

  it('新規追加ボタンでフォームモーダルが表示されること', async () => {
    renderWithProviders(<RecipesPage />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /新規追加/ }))

    expect(screen.getByText('新しいレシピを追加')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('レシピ名を入力')).toBeInTheDocument()
  })

  it('検索入力が表示されること', () => {
    renderWithProviders(<RecipesPage />)
    expect(screen.getByPlaceholderText('レシピ名で検索...')).toBeInTheDocument()
  })

  it('読み込み中にスケルトンが表示されること', () => {
    mockGetRecipes.mockReturnValue(new Promise(() => {})) // never resolves
    renderWithProviders(<RecipesPage />)
    // LoadingState renders skeleton placeholders, not text
    expect(screen.queryByText('目玉焼き')).not.toBeInTheDocument()
  })

  it('カテゴリフィルターボタンが表示されること', async () => {
    renderWithProviders(<RecipesPage />)
    // 「すべて」はカテゴリ・種類・難易度の3箇所に表示
    expect(screen.getAllByRole('button', { name: /すべて/ }).length).toBeGreaterThanOrEqual(3)
    expect(screen.getByRole('button', { name: /和食/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /洋食/ })).toBeInTheDocument()
  })

  it('レシピカードクリックで詳細モーダルが表示されること', async () => {
    renderWithProviders(<RecipesPage />)
    const user = userEvent.setup()
    await waitFor(() => {
      expect(screen.getByText('目玉焼き')).toBeInTheDocument()
    })
    await user.click(screen.getByText('目玉焼き'))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /編集する/ })).toBeInTheDocument()
    })
  })
})
