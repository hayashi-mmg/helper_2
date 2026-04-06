import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ProfilePage from '../ProfilePage'
import { renderWithProviders, mockSeniorUser } from '@/test-utils'
import { useAuthStore } from '@/stores/auth'

const mockChangePassword = vi.fn()

vi.mock('@/api/users', () => ({
  getProfile: vi.fn().mockResolvedValue({
    id: 'user-1', email: 'senior@test.com', full_name: 'テスト太郎', role: 'senior',
    phone: '090-1234-5678', address: '東京都渋谷区', emergency_contact: '090-9876-5432',
    medical_notes: '高血圧', care_level: 2, is_active: true, created_at: '2025-01-01T00:00:00',
  }),
  updateProfile: vi.fn().mockResolvedValue({
    id: 'user-1', email: 'senior@test.com', full_name: '更新太郎', role: 'senior',
    phone: '090-1234-5678', address: '東京都渋谷区', emergency_contact: '090-9876-5432',
    medical_notes: '高血圧', care_level: 2, is_active: true, created_at: '2025-01-01T00:00:00',
  }),
  changePassword: (...args: unknown[]) => mockChangePassword(...args),
}))

describe('ProfilePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().setAuth('token', 'refresh', mockSeniorUser)
  })

  it('見出しが表示されること', async () => {
    renderWithProviders(<ProfilePage />)
    await waitFor(() => {
      expect(screen.getByText('プロファイル')).toBeInTheDocument()
    })
  })

  it('プロファイル情報が表示されること', async () => {
    renderWithProviders(<ProfilePage />)
    await waitFor(() => {
      expect(screen.getByText('senior@test.com')).toBeInTheDocument()
      expect(screen.getByText('テスト太郎')).toBeInTheDocument()
      expect(screen.getByText('090-1234-5678')).toBeInTheDocument()
      expect(screen.getByText('東京都渋谷区')).toBeInTheDocument()
    })
  })

  it('ロール表示がされること', async () => {
    renderWithProviders(<ProfilePage />)
    await waitFor(() => {
      expect(screen.getByText('利用者')).toBeInTheDocument()
    })
  })

  it('編集ボタンが表示されること', async () => {
    renderWithProviders(<ProfilePage />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: '編集' })).toBeInTheDocument()
    })
  })

  it('編集モードに切り替えられること', async () => {
    renderWithProviders(<ProfilePage />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByRole('button', { name: '編集' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: '編集' }))
    expect(screen.getByRole('button', { name: '保存' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'キャンセル' })).toBeInTheDocument()
  })

  it('キャンセルで表示モードに戻ること', async () => {
    renderWithProviders(<ProfilePage />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByRole('button', { name: '編集' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: '編集' }))
    await user.click(screen.getByRole('button', { name: 'キャンセル' }))
    expect(screen.getByRole('button', { name: '編集' })).toBeInTheDocument()
  })

  it('緊急連絡先・医療メモが表示されること', async () => {
    renderWithProviders(<ProfilePage />)
    await waitFor(() => {
      expect(screen.getByText('090-9876-5432')).toBeInTheDocument()
      expect(screen.getByText('高血圧')).toBeInTheDocument()
    })
  })

  it('パスワード変更ボタンが表示されること', async () => {
    renderWithProviders(<ProfilePage />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'パスワード変更' })).toBeInTheDocument()
    })
  })

  it('パスワード変更フォームが表示されること', async () => {
    renderWithProviders(<ProfilePage />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByRole('button', { name: 'パスワード変更' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'パスワード変更' }))
    expect(screen.getByText('現在のパスワード')).toBeInTheDocument()
    expect(screen.getByText('新しいパスワード')).toBeInTheDocument()
    expect(screen.getByText('新しいパスワード（確認）')).toBeInTheDocument()
  })

  it('パスワード変更フォームをキャンセルできること', async () => {
    renderWithProviders(<ProfilePage />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByRole('button', { name: 'パスワード変更' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'パスワード変更' }))
    await user.click(screen.getByRole('button', { name: 'キャンセル' }))
    expect(screen.getByRole('button', { name: 'パスワード変更' })).toBeInTheDocument()
  })

  it('パスワード不一致でエラーが表示されること', async () => {
    renderWithProviders(<ProfilePage />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByRole('button', { name: 'パスワード変更' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'パスワード変更' }))

    const inputs = screen.getAllByDisplayValue('')
    const passwordInputs = inputs.filter(el => el.getAttribute('type') === 'password')
    await user.type(passwordInputs[0], 'currentpass')
    await user.type(passwordInputs[1], 'newpassword1')
    await user.type(passwordInputs[2], 'newpassword2')
    await user.click(screen.getByRole('button', { name: '変更する' }))

    expect(screen.getByText('新しいパスワードが一致しません')).toBeInTheDocument()
  })

  it('短すぎるパスワードでエラーが表示されること', async () => {
    renderWithProviders(<ProfilePage />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByRole('button', { name: 'パスワード変更' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'パスワード変更' }))

    const inputs = screen.getAllByDisplayValue('')
    const passwordInputs = inputs.filter(el => el.getAttribute('type') === 'password')
    await user.type(passwordInputs[0], 'currentpass')
    await user.type(passwordInputs[1], 'short')
    await user.type(passwordInputs[2], 'short')
    await user.click(screen.getByRole('button', { name: '変更する' }))

    expect(screen.getByText('新しいパスワードは8文字以上で入力してください')).toBeInTheDocument()
  })

  it('パスワード変更が成功すること', async () => {
    mockChangePassword.mockResolvedValue({ message: 'パスワードを変更しました' })
    renderWithProviders(<ProfilePage />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByRole('button', { name: 'パスワード変更' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'パスワード変更' }))

    const inputs = screen.getAllByDisplayValue('')
    const passwordInputs = inputs.filter(el => el.getAttribute('type') === 'password')
    await user.type(passwordInputs[0], 'password123')
    await user.type(passwordInputs[1], 'newpassword456')
    await user.type(passwordInputs[2], 'newpassword456')
    await user.click(screen.getByRole('button', { name: '変更する' }))

    await waitFor(() => {
      expect(mockChangePassword).toHaveBeenCalledWith('password123', 'newpassword456')
    })
  })
})
