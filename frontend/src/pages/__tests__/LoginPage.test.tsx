import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LoginPage from '../LoginPage'
import { renderWithProviders } from '@/test-utils'

// API モック
const mockLogin = vi.fn()
const mockValidateQR = vi.fn()
vi.mock('@/api/auth', () => ({
  login: (...args: unknown[]) => mockLogin(...args),
  validateQR: (...args: unknown[]) => mockValidateQR(...args),
}))

// navigate モック
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('パスワードログイン', () => {
    it('メールとパスワードフィールドが表示されること', () => {
      renderWithProviders(<LoginPage />, { initialEntries: ['/login'] })
      expect(screen.getByPlaceholderText('メールアドレス')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('パスワード')).toBeInTheDocument()
    })

    it('タイトルが表示されること', () => {
      renderWithProviders(<LoginPage />, { initialEntries: ['/login'] })
      expect(screen.getByText('ホームヘルパー管理システム')).toBeInTheDocument()
    })

    it('ログインボタンが表示されること', () => {
      renderWithProviders(<LoginPage />, { initialEntries: ['/login'] })
      expect(screen.getByRole('button', { name: 'ログイン' })).toBeInTheDocument()
    })

    it('ログイン成功時にダッシュボードにリダイレクトすること', async () => {
      mockLogin.mockResolvedValue({
        access_token: 'token',
        refresh_token: 'refresh',
        user: { id: '1', email: 'test@test.com', full_name: 'テスト', role: 'senior' },
      })

      renderWithProviders(<LoginPage />, { initialEntries: ['/login'] })
      const user = userEvent.setup()

      await user.type(screen.getByPlaceholderText('メールアドレス'), 'test@test.com')
      await user.type(screen.getByPlaceholderText('パスワード'), 'password')
      await user.click(screen.getByRole('button', { name: 'ログイン' }))

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/')
      })
    })

    it('ログイン失敗時にエラーメッセージが表示されること', async () => {
      mockLogin.mockRejectedValue(new Error('401'))

      renderWithProviders(<LoginPage />, { initialEntries: ['/login'] })
      const user = userEvent.setup()

      await user.type(screen.getByPlaceholderText('メールアドレス'), 'bad@test.com')
      await user.type(screen.getByPlaceholderText('パスワード'), 'wrong')
      await user.click(screen.getByRole('button', { name: 'ログイン' }))

      await waitFor(() => {
        expect(screen.getByText(/正しくありません/)).toBeInTheDocument()
      })
    })
  })

  describe('QRコードログイン', () => {
    it('QRモードに切り替えるとQRトークン入力が表示されること', async () => {
      renderWithProviders(<LoginPage />, { initialEntries: ['/login'] })
      const user = userEvent.setup()

      await user.click(screen.getByRole('button', { name: 'QRコード' }))

      expect(screen.getByPlaceholderText('QRトークン')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'QRコードでログイン' })).toBeInTheDocument()
    })

    it('QRログイン成功時にリダイレクトすること', async () => {
      mockValidateQR.mockResolvedValue({
        access_token: 'token',
        refresh_token: 'refresh',
        user: { id: '1', email: 'test@test.com', full_name: 'テスト', role: 'senior' },
      })

      renderWithProviders(<LoginPage />, { initialEntries: ['/login'] })
      const user = userEvent.setup()

      await user.click(screen.getByRole('button', { name: 'QRコード' }))
      await user.type(screen.getByPlaceholderText('QRトークン'), 'valid-token')
      await user.click(screen.getByRole('button', { name: 'QRコードでログイン' }))

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/')
      })
    })

    it('QRログイン失敗時にエラーメッセージが表示されること', async () => {
      mockValidateQR.mockRejectedValue(new Error('401'))

      renderWithProviders(<LoginPage />, { initialEntries: ['/login'] })
      const user = userEvent.setup()

      await user.click(screen.getByRole('button', { name: 'QRコード' }))
      await user.type(screen.getByPlaceholderText('QRトークン'), 'invalid-token')
      await user.click(screen.getByRole('button', { name: 'QRコードでログイン' }))

      await waitFor(() => {
        expect(screen.getByText(/無効または期限切れ/)).toBeInTheDocument()
      })
    })
  })

  describe('モード切替', () => {
    it('パスワードとQRモードを切り替えられること', async () => {
      renderWithProviders(<LoginPage />, { initialEntries: ['/login'] })
      const user = userEvent.setup()

      // 初期: パスワードモード
      expect(screen.getByPlaceholderText('メールアドレス')).toBeInTheDocument()

      // QRモードに切替
      await user.click(screen.getByRole('button', { name: 'QRコード' }))
      expect(screen.getByPlaceholderText('QRトークン')).toBeInTheDocument()

      // パスワードモードに戻す
      await user.click(screen.getByRole('button', { name: 'パスワード' }))
      expect(screen.getByPlaceholderText('メールアドレス')).toBeInTheDocument()
    })
  })
})
