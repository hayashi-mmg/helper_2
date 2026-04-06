import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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
  updateWeeklyMenu: vi.fn().mockResolvedValue({}),
  copyWeeklyMenu: vi.fn(),
  clearWeeklyMenu: vi.fn(),
}))

vi.mock('@/api/recipes', () => ({
  getRecipes: vi.fn().mockResolvedValue({
    recipes: [
      { id: 'r1', name: '目玉焼き', category: '和食', type: '主菜', difficulty: '簡単', cooking_time: 5, created_at: '2025-01-01', updated_at: '2025-01-01' },
      { id: 'r2', name: 'カレーライス', category: '洋食', type: '主菜', difficulty: '普通', cooking_time: 45, created_at: '2025-01-01', updated_at: '2025-01-01' },
      { id: 'r3', name: '味噌汁', category: '和食', type: '汁物', difficulty: '簡単', cooking_time: 10, created_at: '2025-01-01', updated_at: '2025-01-01' },
      { id: 'r4', name: '麻婆豆腐', category: '中華', type: '主菜', difficulty: '難しい', cooking_time: 30, created_at: '2025-01-01', updated_at: '2025-01-01' },
      { id: 'r5', name: 'サラダ', category: 'その他', type: '副菜', difficulty: '簡単', cooking_time: 5, created_at: '2025-01-01', updated_at: '2025-01-01' },
    ],
    pagination: { page: 1, limit: 100, total: 5, total_pages: 1, has_next: false, has_prev: false },
  }),
}))

const allRecipeNames = ['目玉焼き', 'カレーライス', '味噌汁', '麻婆豆腐', 'サラダ']

async function openRecipePicker() {
  const user = userEvent.setup()
  renderWithProviders(<MenuPage />)
  await waitFor(() => {
    expect(screen.getAllByRole('button', { name: /レシピを追加/ }).length).toBe(14)
  })
  // Click the first "レシピを追加" button (Monday breakfast)
  await user.click(screen.getAllByRole('button', { name: /レシピを追加/ })[0])
  await waitFor(() => {
    expect(screen.getByText('レシピを選択')).toBeInTheDocument()
  })
  return user
}

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

describe('MenuPage - レシピピッカー', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().setAuth('token', 'refresh', mockSeniorUser)
  })

  it('レシピ追加ボタンでピッカーモーダルが開くこと', async () => {
    await openRecipePicker()
    expect(screen.getByText('レシピを選択')).toBeInTheDocument()
    expect(screen.getByText('月曜日 朝食')).toBeInTheDocument()
  })

  it('検索入力欄が表示されること', async () => {
    await openRecipePicker()
    expect(screen.getByPlaceholderText('レシピ名で検索...')).toBeInTheDocument()
  })

  it('全レシピが表示されること', async () => {
    await openRecipePicker()
    for (const name of allRecipeNames) {
      expect(screen.getByText(name)).toBeInTheDocument()
    }
  })

  it('カテゴリ・種類・難易度のフィルターラベルが表示されること', async () => {
    await openRecipePicker()
    expect(screen.getByText('カテゴリ')).toBeInTheDocument()
    expect(screen.getByText('種類')).toBeInTheDocument()
    expect(screen.getByText('難易度')).toBeInTheDocument()
  })

  it('カテゴリフィルターボタンが表示されること', async () => {
    await openRecipePicker()
    expect(screen.getByRole('button', { name: /🍱 和食/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /🍝 洋食/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /🥡 中華/ })).toBeInTheDocument()
  })

  it('種類フィルターボタンが表示されること', async () => {
    await openRecipePicker()
    // 主菜 appears in both filter and recipe badges - check button specifically
    const typeButtons = screen.getAllByRole('button', { name: '主菜' })
    expect(typeButtons.length).toBeGreaterThanOrEqual(1)
    expect(screen.getByRole('button', { name: '副菜' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '汁物' })).toBeInTheDocument()
  })

  it('難易度フィルターボタンが表示されること', async () => {
    await openRecipePicker()
    const easyButtons = screen.getAllByRole('button', { name: '簡単' })
    expect(easyButtons.length).toBeGreaterThanOrEqual(1)
    expect(screen.getByRole('button', { name: '普通' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '難しい' })).toBeInTheDocument()
  })

  it('カテゴリフィルターで和食のみ表示されること', async () => {
    const user = await openRecipePicker()
    await user.click(screen.getByRole('button', { name: /🍱 和食/ }))
    await waitFor(() => {
      expect(screen.getByText('目玉焼き')).toBeInTheDocument()
      expect(screen.getByText('味噌汁')).toBeInTheDocument()
      expect(screen.queryByText('カレーライス')).not.toBeInTheDocument()
      expect(screen.queryByText('麻婆豆腐')).not.toBeInTheDocument()
      expect(screen.queryByText('サラダ')).not.toBeInTheDocument()
    })
  })

  it('カテゴリフィルターで中華のみ表示されること', async () => {
    const user = await openRecipePicker()
    await user.click(screen.getByRole('button', { name: /🥡 中華/ }))
    await waitFor(() => {
      expect(screen.getByText('麻婆豆腐')).toBeInTheDocument()
      expect(screen.queryByText('目玉焼き')).not.toBeInTheDocument()
      expect(screen.queryByText('カレーライス')).not.toBeInTheDocument()
    })
  })

  it('種類フィルターで汁物のみ表示されること', async () => {
    const user = await openRecipePicker()
    // Find the filter button for 汁物 (not badge)
    await user.click(screen.getByRole('button', { name: '汁物' }))
    await waitFor(() => {
      expect(screen.getByText('味噌汁')).toBeInTheDocument()
      expect(screen.queryByText('目玉焼き')).not.toBeInTheDocument()
      expect(screen.queryByText('カレーライス')).not.toBeInTheDocument()
      expect(screen.queryByText('麻婆豆腐')).not.toBeInTheDocument()
    })
  })

  it('難易度フィルターで簡単のみ表示されること', async () => {
    const user = await openRecipePicker()
    // Click the filter button for 簡単
    const easyButtons = screen.getAllByRole('button', { name: '簡単' })
    await user.click(easyButtons[0])
    await waitFor(() => {
      expect(screen.getByText('目玉焼き')).toBeInTheDocument()
      expect(screen.getByText('味噌汁')).toBeInTheDocument()
      expect(screen.getByText('サラダ')).toBeInTheDocument()
      expect(screen.queryByText('カレーライス')).not.toBeInTheDocument()
      expect(screen.queryByText('麻婆豆腐')).not.toBeInTheDocument()
    })
  })

  it('カテゴリ+種類の複合フィルターが動作すること', async () => {
    const user = await openRecipePicker()
    // Filter: 和食 + 主菜 → 目玉焼きのみ
    await user.click(screen.getByRole('button', { name: /🍱 和食/ }))
    const mainDishButtons = screen.getAllByRole('button', { name: '主菜' })
    await user.click(mainDishButtons[0])
    await waitFor(() => {
      expect(screen.getByText('目玉焼き')).toBeInTheDocument()
      expect(screen.queryByText('味噌汁')).not.toBeInTheDocument()
      expect(screen.queryByText('カレーライス')).not.toBeInTheDocument()
    })
  })

  it('テキスト検索が動作すること', async () => {
    const user = await openRecipePicker()
    await user.type(screen.getByPlaceholderText('レシピ名で検索...'), 'カレー')
    await waitFor(() => {
      expect(screen.getByText('カレーライス')).toBeInTheDocument()
      expect(screen.queryByText('目玉焼き')).not.toBeInTheDocument()
      expect(screen.queryByText('味噌汁')).not.toBeInTheDocument()
    })
  })

  it('フィルター+テキスト検索の組み合わせが動作すること', async () => {
    const user = await openRecipePicker()
    // Filter: 和食 + search "味噌"
    await user.click(screen.getByRole('button', { name: /🍱 和食/ }))
    await user.type(screen.getByPlaceholderText('レシピ名で検索...'), '味噌')
    await waitFor(() => {
      expect(screen.getByText('味噌汁')).toBeInTheDocument()
      expect(screen.queryByText('目玉焼き')).not.toBeInTheDocument()
    })
  })

  it('該当レシピがない場合にメッセージが表示されること', async () => {
    const user = await openRecipePicker()
    await user.type(screen.getByPlaceholderText('レシピ名で検索...'), 'zzzzzzz')
    await waitFor(() => {
      expect(screen.getByText('レシピが見つかりません')).toBeInTheDocument()
    })
  })

  it('すべてボタンでフィルターがリセットされること', async () => {
    const user = await openRecipePicker()
    // Apply 和食 filter
    await user.click(screen.getByRole('button', { name: /🍱 和食/ }))
    await waitFor(() => {
      expect(screen.queryByText('カレーライス')).not.toBeInTheDocument()
    })
    // Click すべて to reset
    const allButtons = screen.getAllByRole('button', { name: 'すべて' })
    // First すべて is for category
    await user.click(allButtons[0])
    await waitFor(() => {
      expect(screen.getByText('カレーライス')).toBeInTheDocument()
      expect(screen.getByText('目玉焼き')).toBeInTheDocument()
    })
  })

  it('閉じるボタンでピッカーが閉じること', async () => {
    const user = await openRecipePicker()
    await user.click(screen.getByRole('button', { name: '閉じる' }))
    await waitFor(() => {
      expect(screen.queryByText('レシピを選択')).not.toBeInTheDocument()
    })
  })

  it('閉じた後に再度開くとフィルターがリセットされていること', async () => {
    const user = await openRecipePicker()
    // Apply filter
    await user.click(screen.getByRole('button', { name: /🍱 和食/ }))
    await waitFor(() => {
      expect(screen.queryByText('カレーライス')).not.toBeInTheDocument()
    })
    // Close
    await user.click(screen.getByRole('button', { name: '閉じる' }))
    await waitFor(() => {
      expect(screen.queryByText('レシピを選択')).not.toBeInTheDocument()
    })
    // Reopen
    await user.click(screen.getAllByRole('button', { name: /レシピを追加/ })[0])
    await waitFor(() => {
      expect(screen.getByText('レシピを選択')).toBeInTheDocument()
      // All recipes should be visible (filters reset)
      for (const name of allRecipeNames) {
        expect(screen.getByText(name)).toBeInTheDocument()
      }
    })
  })
})
