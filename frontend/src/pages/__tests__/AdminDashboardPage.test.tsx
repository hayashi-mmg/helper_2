import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import AdminDashboardPage from '../AdminDashboardPage'
import { renderWithProviders, mockAdminUser } from '@/test-utils'
import { useAuthStore } from '@/stores/auth'

const mockGetDashboardStats = vi.fn()

vi.mock('@/api/admin', () => ({
  getDashboardStats: (...args: unknown[]) => mockGetDashboardStats(...args),
}))

describe('AdminDashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().setAuth('token', 'refresh', mockAdminUser)
    mockGetDashboardStats.mockResolvedValue({
      total_users: 150,
      users_by_role: { senior: 80, helper: 50, care_manager: 15, system_admin: 5 },
      active_users: 140,
      inactive_users: 10,
      new_users_this_month: 12,
      active_assignments: 95,
      tasks_completed_this_week: 230,
      login_count_today: 85,
      generated_at: '2026-04-04T12:00:00Z',
    })
  })

  it('管理ダッシュボードの見出しが表示されること', async () => {
    renderWithProviders(<AdminDashboardPage />)
    await waitFor(() => {
      expect(screen.getByText('管理ダッシュボード')).toBeInTheDocument()
    })
  })

  it('統計データが表示されること', async () => {
    renderWithProviders(<AdminDashboardPage />)
    await waitFor(() => {
      expect(screen.getByText('150')).toBeInTheDocument()
      expect(screen.getByText('140')).toBeInTheDocument()
      expect(screen.getByText('95')).toBeInTheDocument()
    })
  })

  it('ロール別ユーザー数が表示されること', async () => {
    renderWithProviders(<AdminDashboardPage />)
    await waitFor(() => {
      expect(screen.getByText('ロール別ユーザー数')).toBeInTheDocument()
      expect(screen.getByText('利用者')).toBeInTheDocument()
      expect(screen.getByText('ヘルパー')).toBeInTheDocument()
    })
  })

  it('今週のアクティビティが表示されること', async () => {
    renderWithProviders(<AdminDashboardPage />)
    await waitFor(() => {
      expect(screen.getByText('今週のアクティビティ')).toBeInTheDocument()
      expect(screen.getByText('230')).toBeInTheDocument()
      expect(screen.getByText('85')).toBeInTheDocument()
    })
  })
})
