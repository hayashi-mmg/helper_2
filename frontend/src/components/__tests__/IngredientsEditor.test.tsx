import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import IngredientsEditor from '../recipes/IngredientsEditor'
import { renderWithProviders, mockSeniorUser } from '@/test-utils'
import { useAuthStore } from '@/stores/auth'

const mockGetIngredients = vi.fn()
const mockUpdateIngredients = vi.fn()

vi.mock('@/api/recipe-ingredients', () => ({
  getRecipeIngredients: (...args: unknown[]) => mockGetIngredients(...args),
  updateRecipeIngredients: (...args: unknown[]) => mockUpdateIngredients(...args),
}))

const emptyResponse = { recipe_id: 'r1', recipe_name: '目玉焼き', ingredients: [] }
const sampleResponse = {
  recipe_id: 'r1',
  recipe_name: '鶏肉の照り焼き',
  ingredients: [
    { id: 'i1', name: '鶏もも肉', quantity: '300g', category: '肉類', sort_order: 1, created_at: '2025-01-01' },
    { id: 'i2', name: 'しょうゆ', quantity: '大さじ2', category: '調味料', sort_order: 2, created_at: '2025-01-01' },
  ],
}

describe('IngredientsEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().setAuth('token', 'refresh', mockSeniorUser)
  })

  it('食材未登録時にメッセージが表示されること', async () => {
    mockGetIngredients.mockResolvedValue(emptyResponse)
    renderWithProviders(<IngredientsEditor recipeId="r1" recipeName="目玉焼き" />)
    await waitFor(() => {
      expect(screen.getByText('食材が登録されていません')).toBeInTheDocument()
    })
  })

  it('食材が表示されること', async () => {
    mockGetIngredients.mockResolvedValue(sampleResponse)
    renderWithProviders(<IngredientsEditor recipeId="r1" recipeName="鶏肉の照り焼き" />)
    await waitFor(() => {
      expect(screen.getByText('鶏もも肉')).toBeInTheDocument()
      expect(screen.getByText('300g')).toBeInTheDocument()
      expect(screen.getByText('しょうゆ')).toBeInTheDocument()
    })
  })

  it('件数が表示されること', async () => {
    mockGetIngredients.mockResolvedValue(sampleResponse)
    renderWithProviders(<IngredientsEditor recipeId="r1" recipeName="鶏肉の照り焼き" />)
    await waitFor(() => {
      expect(screen.getByText('構造化食材 (2件)')).toBeInTheDocument()
    })
  })

  it('編集ボタンが表示されること', async () => {
    mockGetIngredients.mockResolvedValue(sampleResponse)
    renderWithProviders(<IngredientsEditor recipeId="r1" recipeName="鶏肉の照り焼き" />)
    await waitFor(() => {
      expect(screen.getByText('編集')).toBeInTheDocument()
    })
  })

  it('編集クリックでフォームが表示されること', async () => {
    mockGetIngredients.mockResolvedValue(sampleResponse)
    const user = userEvent.setup()
    renderWithProviders(<IngredientsEditor recipeId="r1" recipeName="鶏肉の照り焼き" />)
    await waitFor(() => screen.getByText('編集'))
    await user.click(screen.getByText('編集'))
    expect(screen.getByText('保存')).toBeInTheDocument()
    expect(screen.getByText('取消')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /食材を追加/ })).toBeInTheDocument()
  })
})
