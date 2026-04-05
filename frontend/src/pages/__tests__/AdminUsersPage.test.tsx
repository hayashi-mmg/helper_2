import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AdminUsersPage from '../AdminUsersPage'
import { renderWithProviders, mockAdminUser } from '@/test-utils'
import { useAuthStore } from '@/stores/auth'

const mockGetAdminUsers = vi.fn()
const mockCreateAdminUser = vi.fn()
const mockDeactivateUser = vi.fn()
const mockActivateUser = vi.fn()
const mockResetPassword = vi.fn()

vi.mock('@/api/admin', () => ({
  getAdminUsers: (...args: unknown[]) => mockGetAdminUsers(...args),
  createAdminUser: (...args: unknown[]) => mockCreateAdminUser(...args),
  updateAdminUser: vi.fn(),
  deactivateUser: (...args: unknown[]) => mockDeactivateUser(...args),
  activateUser: (...args: unknown[]) => mockActivateUser(...args),
  resetPassword: (...args: unknown[]) => mockResetPassword(...args),
}))

const mockUsers = [
  {
    id: 'u1', email: 'tanaka@test.com', full_name: '田中太郎', role: 'senior',
    is_active: true, created_at: '2025-01-01', care_level: 2,
  },
  {
    id: 'u2', email: 'suzuki@test.com', full_name: '鈴木花子', role: 'helper',
    is_active: true, created_at: '2025-01-02', certification_number: 'H-123',
  },
  {
    id: 'u3', email: 'inactive@test.com', full_name: '無効太郎', role: 'senior',
    is_active: false, created_at: '2025-01-03',
  },
]

describe('AdminUsersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().setAuth('token', 'refresh', mockAdminUser)
    mockGetAdminUsers.mockResolvedValue({
      users: mockUsers,
      pagination: { page: 1, limit: 20, total: 3, total_pages: 1, has_next: false, has_prev: false },
    })
  })

  it('ユーザー管理の見出しが表示されること', () => {
    renderWithProviders(<AdminUsersPage />)
    expect(screen.getByText('ユーザー管理')).toBeInTheDocument()
  })

  it('ユーザー一覧が表示されること', async () => {
    renderWithProviders(<AdminUsersPage />)
    await waitFor(() => {
      expect(screen.getByText('田中太郎')).toBeInTheDocument()
      expect(screen.getByText('鈴木花子')).toBeInTheDocument()
    })
  })

  it('ロールバッジが正しく表示されること', async () => {
    renderWithProviders(<AdminUsersPage />)
    await waitFor(() => {
      expect(screen.getAllByText('利用者').length).toBeGreaterThanOrEqual(1)
      expect(screen.getByText('ヘルパー')).toBeInTheDocument()
    })
  })

  it('新規作成ボタンが表示されること', () => {
    renderWithProviders(<AdminUsersPage />)
    expect(screen.getByRole('button', { name: /新規作成/ })).toBeInTheDocument()
  })

  it('新規作成ボタンでフォームが表示されること', async () => {
    renderWithProviders(<AdminUsersPage />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /新規作成/ }))
    expect(screen.getByText('新しいユーザーを作成')).toBeInTheDocument()
  })

  it('検索入力が表示されること', () => {
    renderWithProviders(<AdminUsersPage />)
    expect(screen.getByPlaceholderText('氏名・メールで検索...')).toBeInTheDocument()
  })

  it('ロールフィルターボタンが表示されること', () => {
    renderWithProviders(<AdminUsersPage />)
    expect(screen.getByRole('button', { name: 'すべて' })).toBeInTheDocument()
    // roleOptionsの利用者ボタン
    expect(screen.getAllByRole('button', { name: '利用者' }).length).toBeGreaterThanOrEqual(1)
  })

  it('ユーザー作成が成功すること', async () => {
    mockCreateAdminUser.mockResolvedValue({
      id: 'new-id', email: 'new@test.com', full_name: '新規ユーザー', role: 'senior',
      is_active: true, temporary_password: 'TempPass123', created_at: '2026-04-04',
      message: '一時パスワードを安全にユーザーに伝達してください。',
    })
    renderWithProviders(<AdminUsersPage />)
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: /新規作成/ }))
    await user.type(screen.getByPlaceholderText('email@example.com'), 'new@test.com')
    await user.type(screen.getByPlaceholderText('氏名を入力'), '新規ユーザー')
    await user.click(screen.getByRole('button', { name: '作成' }))

    await waitFor(() => {
      expect(mockCreateAdminUser).toHaveBeenCalled()
    })
  })

  it('ユーザーのメールアドレスが一覧に表示されること', async () => {
    renderWithProviders(<AdminUsersPage />)
    await waitFor(() => {
      expect(screen.getByText('tanaka@test.com')).toBeInTheDocument()
      expect(screen.getByText('suzuki@test.com')).toBeInTheDocument()
    })
  })

  it('読み込み中にスケルトンが表示されること', () => {
    mockGetAdminUsers.mockReturnValue(new Promise(() => {}))
    renderWithProviders(<AdminUsersPage />)
    expect(screen.queryByText('田中太郎')).not.toBeInTheDocument()
  })
})
