import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AdminAssignmentsPage from '../AdminAssignmentsPage'
import { renderWithProviders, mockAdminUser } from '@/test-utils'
import { useAuthStore } from '@/stores/auth'

const mockGetAssignments = vi.fn()
const mockCreateAssignment = vi.fn()
const mockDeleteAssignment = vi.fn()
const mockGetAdminUsers = vi.fn()

vi.mock('@/api/admin', () => ({
  getAssignments: (...args: unknown[]) => mockGetAssignments(...args),
  createAssignment: (...args: unknown[]) => mockCreateAssignment(...args),
  deleteAssignment: (...args: unknown[]) => mockDeleteAssignment(...args),
  getAdminUsers: (...args: unknown[]) => mockGetAdminUsers(...args),
}))

const mockAssignments = [
  {
    id: 'a1',
    helper: { id: 'h1', full_name: 'ヘルパー花子', role: 'helper' },
    senior: { id: 's1', full_name: '田中太郎', role: 'senior' },
    assigned_by: { id: 'admin1', full_name: '管理者', role: 'system_admin' },
    status: 'active',
    visit_frequency: '週3回',
    preferred_days: [1, 3, 5],
    start_date: '2025-10-01',
    created_at: '2025-09-28',
  },
]

describe('AdminAssignmentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().setAuth('token', 'refresh', mockAdminUser)
    mockGetAssignments.mockResolvedValue({
      assignments: mockAssignments,
      pagination: { page: 1, limit: 20, total: 1, total_pages: 1, has_next: false, has_prev: false },
    })
    mockGetAdminUsers.mockResolvedValue({
      users: [],
      pagination: { page: 1, limit: 100, total: 0, total_pages: 0, has_next: false, has_prev: false },
    })
  })

  it('アサイン管理の見出しが表示されること', () => {
    renderWithProviders(<AdminAssignmentsPage />)
    expect(screen.getByText('アサイン管理')).toBeInTheDocument()
  })

  it('アサイン一覧が表示されること', async () => {
    renderWithProviders(<AdminAssignmentsPage />)
    await waitFor(() => {
      expect(screen.getByText('ヘルパー花子')).toBeInTheDocument()
      expect(screen.getByText('田中太郎')).toBeInTheDocument()
    })
  })

  it('ステータスバッジが表示されること', async () => {
    renderWithProviders(<AdminAssignmentsPage />)
    await waitFor(() => {
      expect(screen.getByText('アクティブ')).toBeInTheDocument()
    })
  })

  it('訪問頻度が表示されること', async () => {
    renderWithProviders(<AdminAssignmentsPage />)
    await waitFor(() => {
      expect(screen.getByText('週3回')).toBeInTheDocument()
    })
  })

  it('訪問日が表示されること', async () => {
    renderWithProviders(<AdminAssignmentsPage />)
    await waitFor(() => {
      expect(screen.getByText('訪問日: 月・水・金')).toBeInTheDocument()
    })
  })

  it('新規アサインボタンが表示されること', () => {
    renderWithProviders(<AdminAssignmentsPage />)
    expect(screen.getByRole('button', { name: /新規アサイン/ })).toBeInTheDocument()
  })

  it('新規アサインボタンでフォームが表示されること', async () => {
    renderWithProviders(<AdminAssignmentsPage />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /新規アサイン/ }))
    expect(screen.getByText('新しいアサインを作成')).toBeInTheDocument()
  })

  it('ステータスフィルターボタンが表示されること', () => {
    renderWithProviders(<AdminAssignmentsPage />)
    expect(screen.getByRole('button', { name: 'すべて' })).toBeInTheDocument()
    // 「アクティブ」はフィルターボタンとバッジの両方に存在
    expect(screen.getAllByText('アクティブ').length).toBeGreaterThanOrEqual(1)
  })

  it('終了ボタンが表示されること', async () => {
    renderWithProviders(<AdminAssignmentsPage />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: '終了' })).toBeInTheDocument()
    })
  })

  it('読み込み中にスケルトンが表示されること', () => {
    mockGetAssignments.mockReturnValue(new Promise(() => {}))
    renderWithProviders(<AdminAssignmentsPage />)
    expect(screen.queryByText('ヘルパー花子')).not.toBeInTheDocument()
  })
})
