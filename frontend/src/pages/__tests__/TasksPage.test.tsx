import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TasksPage from '../TasksPage'
import { renderWithProviders, mockHelperUser } from '@/test-utils'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/api/tasks', () => ({
  getTodayTasks: vi.fn().mockResolvedValue([
    { id: 't1', senior_user_id: 'u1', helper_user_id: 'user-2', title: '朝食の準備', task_type: 'cooking', priority: 'high', status: 'pending', scheduled_date: '2025-07-14', estimated_minutes: 30, created_at: '2025-01-01', updated_at: '2025-01-01' },
    { id: 't2', senior_user_id: 'u1', helper_user_id: 'user-2', title: '掃除', task_type: 'cleaning', priority: 'medium', status: 'in_progress', scheduled_date: '2025-07-14', created_at: '2025-01-01', updated_at: '2025-01-01' },
  ]),
  createTask: vi.fn(),
  updateTask: vi.fn(),
  deleteTask: vi.fn(),
  completeTask: vi.fn(),
}))

describe('TasksPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().setAuth('token', 'refresh', mockHelperUser)
  })

  it('見出しが表示されること', () => {
    renderWithProviders(<TasksPage />)
    expect(screen.getByText('作業管理')).toBeInTheDocument()
  })

  it('タスクが一覧表示されること', async () => {
    renderWithProviders(<TasksPage />)
    await waitFor(() => {
      expect(screen.getByText('朝食の準備')).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('新規追加ボタンが表示されること', () => {
    renderWithProviders(<TasksPage />)
    expect(screen.getByRole('button', { name: '新規追加' })).toBeInTheDocument()
  })

  it('新規追加でフォームが表示されること', async () => {
    renderWithProviders(<TasksPage />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: '新規追加' }))
    expect(screen.getByPlaceholderText('作業名')).toBeInTheDocument()
  })
})
