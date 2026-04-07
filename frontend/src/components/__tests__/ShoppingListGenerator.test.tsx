import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ShoppingListGenerator from '../menu/ShoppingListGenerator'
import { renderWithProviders, mockSeniorUser } from '@/test-utils'
import { useAuthStore } from '@/stores/auth'

const mockGenerateFromMenu = vi.fn()
const mockToggleExclude = vi.fn()

vi.mock('@/api/shopping', () => ({
  generateFromMenu: (...args: unknown[]) => mockGenerateFromMenu(...args),
  toggleExclude: (...args: unknown[]) => mockToggleExclude(...args),
  getShoppingRequests: vi.fn().mockResolvedValue([]),
  createShoppingRequest: vi.fn(),
  updateShoppingItem: vi.fn(),
}))

const mockResult = {
  id: 'req-1',
  request_date: '2025-07-14',
  status: 'pending',
  notes: null,
  source_menu_week: '2025-07-14',
  items: [
    {
      id: 'item-1',
      item_name: '鶏もも肉',
      category: '肉類',
      quantity: '（照り焼き 300g + 親子丼 200g）',
      status: 'pending',
      is_excluded: false,
      excluded_reason: null,
      recipe_sources: ['鶏肉の照り焼き', '親子丼'],
    },
    {
      id: 'item-2',
      item_name: 'しょうゆ',
      category: '調味料',
      quantity: '大さじ4',
      status: 'pending',
      is_excluded: true,
      excluded_reason: 'pantry',
      recipe_sources: ['鶏肉の照り焼き', '親子丼'],
    },
  ],
  summary: { total_items: 2, excluded_items: 1, active_items: 1 },
  created_at: '2025-07-14T00:00:00Z',
}

describe('ShoppingListGenerator', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().setAuth('token', 'refresh', mockSeniorUser)
  })

  it('レシピがない場合はボタンが無効', () => {
    renderWithProviders(<ShoppingListGenerator weekStart="2025-07-14" hasRecipes={false} />)
    const button = screen.getByText('この献立から買い物リストを作成')
    expect(button.closest('button')).toBeDisabled()
  })

  it('レシピがある場合はボタンが有効', () => {
    renderWithProviders(<ShoppingListGenerator weekStart="2025-07-14" hasRecipes={true} />)
    const button = screen.getByText('この献立から買い物リストを作成')
    expect(button.closest('button')).not.toBeDisabled()
  })

  it('ボタンクリックでフォームが表示される', async () => {
    const user = userEvent.setup()
    renderWithProviders(<ShoppingListGenerator weekStart="2025-07-14" hasRecipes={true} />)
    await user.click(screen.getByText('この献立から買い物リストを作成'))
    expect(screen.getByText('買い物リストを生成')).toBeInTheDocument()
    expect(screen.getByText('生成する')).toBeInTheDocument()
  })

  it('生成後に結果が表示される', async () => {
    mockGenerateFromMenu.mockResolvedValue(mockResult)
    const user = userEvent.setup()
    renderWithProviders(<ShoppingListGenerator weekStart="2025-07-14" hasRecipes={true} />)

    await user.click(screen.getByText('この献立から買い物リストを作成'))
    await user.click(screen.getByText('生成する'))

    await waitFor(() => {
      expect(screen.getByText('鶏もも肉')).toBeInTheDocument()
      expect(screen.getByText('しょうゆ')).toBeInTheDocument()
      expect(screen.getByText('在庫あり')).toBeInTheDocument()
    })
  })

  it('除外アイテムに取り消し線が表示される', async () => {
    mockGenerateFromMenu.mockResolvedValue(mockResult)
    const user = userEvent.setup()
    renderWithProviders(<ShoppingListGenerator weekStart="2025-07-14" hasRecipes={true} />)

    await user.click(screen.getByText('この献立から買い物リストを作成'))
    await user.click(screen.getByText('生成する'))

    await waitFor(() => {
      const soyText = screen.getByText('しょうゆ')
      expect(soyText).toHaveStyle('text-decoration: line-through')
    })
  })

  it('サマリーが正しく表示される', async () => {
    mockGenerateFromMenu.mockResolvedValue(mockResult)
    const user = userEvent.setup()
    renderWithProviders(<ShoppingListGenerator weekStart="2025-07-14" hasRecipes={true} />)

    await user.click(screen.getByText('この献立から買い物リストを作成'))
    await user.click(screen.getByText('生成する'))

    await waitFor(() => {
      expect(screen.getByText('合計: 2品')).toBeInTheDocument()
      expect(screen.getByText('除外: 1品')).toBeInTheDocument()
      expect(screen.getByText('購入対象: 1品')).toBeInTheDocument()
    })
  })

  it('出典レシピが表示される', async () => {
    mockGenerateFromMenu.mockResolvedValue(mockResult)
    const user = userEvent.setup()
    renderWithProviders(<ShoppingListGenerator weekStart="2025-07-14" hasRecipes={true} />)

    await user.click(screen.getByText('この献立から買い物リストを作成'))
    await user.click(screen.getByText('生成する'))

    await waitFor(() => {
      // テキストが複数ノードに分割される場合があるため部分一致で検証
      const sourceElements = screen.getAllByText(/鶏肉の照り焼き/)
      expect(sourceElements.length).toBeGreaterThan(0)
    })
  })
})
