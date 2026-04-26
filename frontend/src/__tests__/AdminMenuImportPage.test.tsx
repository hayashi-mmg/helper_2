import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '@/test-utils'
import AdminMenuImportPage from '@/pages/AdminMenuImportPage'

const mockGetAdminUsers = vi.fn()
const mockImportMenu = vi.fn()

vi.mock('@/api/admin', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/admin')>()
  return {
    ...actual,
    getAdminUsers: (...args: unknown[]) => mockGetAdminUsers(...args),
    importMenu: (...args: unknown[]) => mockImportMenu(...args),
  }
})

vi.mock('@/components/ui/toaster', () => ({
  toaster: { create: vi.fn(), success: vi.fn() },
}))

const validJson = JSON.stringify({
  week_start: '2026-04-27',
  recipes: [
    {
      name: '鶏の照り焼き',
      category: '和食',
      type: '主菜',
      difficulty: '簡単',
      cooking_time: 20,
      ingredients_text: '鶏もも肉 300g',
    },
  ],
  menu: {
    monday: { breakfast: [], dinner: [{ recipe_name: '鶏の照り焼き', recipe_type: '主菜' }] },
    tuesday: { breakfast: [], dinner: [] },
    wednesday: { breakfast: [], dinner: [] },
    thursday: { breakfast: [], dinner: [] },
    friday: { breakfast: [], dinner: [] },
    saturday: { breakfast: [], dinner: [] },
    sunday: { breakfast: [], dinner: [] },
  },
})

const baseUsers = {
  users: [
    { id: 'u-1', email: 'senior@test.com', full_name: 'テスト太郎', role: 'senior' },
  ],
  pagination: { page: 1, limit: 100, total: 1, total_pages: 1, has_next: false, has_prev: false },
}

describe('AdminMenuImportPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetAdminUsers.mockResolvedValue(baseUsers)
  })

  it('ユーザー選択肢がレンダリングされること', async () => {
    renderWithProviders(<AdminMenuImportPage />)
    await waitFor(() => {
      expect(screen.getByText(/テスト太郎/)).toBeInTheDocument()
    })
  })

  it('プレビューボタンで dry_run=true でAPIを呼ぶこと', async () => {
    mockImportMenu.mockResolvedValue({
      applied: false,
      target_user: { id: 'u-1', email: 'senior@test.com', full_name: 'テスト太郎', role: 'senior' },
      week_start: '2026-04-27',
      created_recipe_count: 1,
      reused_recipe_count: 0,
      replaced_menu: false,
      shopping_list: { request_id: 'r-1', total_items: 3, excluded_items: 0, active_items: 3, replaced_existing: false },
      warnings: [],
    })

    renderWithProviders(<AdminMenuImportPage />)
    await waitFor(() => expect(screen.getByText(/テスト太郎/)).toBeInTheDocument())

    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'u-1' } })
    fireEvent.change(screen.getByPlaceholderText(/week_start/), { target: { value: validJson } })

    fireEvent.click(screen.getByRole('button', { name: 'プレビュー' }))

    await waitFor(() => {
      expect(mockImportMenu).toHaveBeenCalled()
    })
    const callArg = mockImportMenu.mock.calls[0][0]
    expect(callArg.dry_run).toBe(true)
    expect(callArg.target_user_id).toBe('u-1')
    expect(await screen.findByText(/プレビュー（DBは未変更）/)).toBeInTheDocument()
  })

  it('本番に取り込むボタンで dry_run=false でAPIを呼び結果を表示すること', async () => {
    mockImportMenu.mockResolvedValue({
      applied: true,
      target_user: { id: 'u-1', email: 'senior@test.com', full_name: 'テスト太郎', role: 'senior' },
      week_start: '2026-04-27',
      created_recipe_count: 1,
      reused_recipe_count: 0,
      replaced_menu: false,
      shopping_list: { request_id: 'r-1', total_items: 3, excluded_items: 1, active_items: 2, replaced_existing: false },
      warnings: [],
    })

    renderWithProviders(<AdminMenuImportPage />)
    await waitFor(() => expect(screen.getByText(/テスト太郎/)).toBeInTheDocument())

    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'u-1' } })
    fireEvent.change(screen.getByPlaceholderText(/week_start/), { target: { value: validJson } })

    fireEvent.click(screen.getByRole('button', { name: '本番に取り込む' }))

    await waitFor(() => {
      expect(mockImportMenu).toHaveBeenCalled()
    })
    const callArg = mockImportMenu.mock.calls[0][0]
    expect(callArg.dry_run).toBe(false)
    expect(callArg.target_user_id).toBe('u-1')
    expect(await screen.findByText(/取り込み完了/)).toBeInTheDocument()
    expect(screen.getByText(/全3件/)).toBeInTheDocument()
  })

  it('不正なJSONではAPIを呼ばないこと', async () => {
    renderWithProviders(<AdminMenuImportPage />)
    await waitFor(() => expect(screen.getByText(/テスト太郎/)).toBeInTheDocument())

    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'u-1' } })
    fireEvent.change(screen.getByPlaceholderText(/week_start/), { target: { value: '{ invalid' } })
    fireEvent.click(screen.getByRole('button', { name: '本番に取り込む' }))

    await waitFor(() => {
      expect(mockImportMenu).not.toHaveBeenCalled()
    })
  })

  it('対象ユーザー未選択ではAPIを呼ばないこと', async () => {
    renderWithProviders(<AdminMenuImportPage />)
    await waitFor(() => expect(screen.getByText(/テスト太郎/)).toBeInTheDocument())

    fireEvent.change(screen.getByPlaceholderText(/week_start/), { target: { value: validJson } })
    fireEvent.click(screen.getByRole('button', { name: '本番に取り込む' }))

    await waitFor(() => {
      expect(mockImportMenu).not.toHaveBeenCalled()
    })
  })
})
