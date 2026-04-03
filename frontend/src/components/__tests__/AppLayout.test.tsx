import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AppLayout from '../layout/AppLayout'
import { renderWithProviders, mockSeniorUser } from '@/test-utils'
import { useAuthStore } from '@/stores/auth'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

describe('AppLayout', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().setAuth('token', 'refresh', mockSeniorUser)
  })

  it('アプリタイトルが表示されること', () => {
    renderWithProviders(<AppLayout />)
    expect(screen.getByText('ヘルパー管理')).toBeInTheDocument()
  })

  it('ユーザー名が表示されること', () => {
    renderWithProviders(<AppLayout />)
    expect(screen.getByText('テスト太郎')).toBeInTheDocument()
  })

  it('ナビリンクが全て表示されること', () => {
    renderWithProviders(<AppLayout />)
    expect(screen.getByRole('button', { name: 'ダッシュボード' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'レシピ' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '献立' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '作業管理' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'メッセージ' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '買い物' })).toBeInTheDocument()
  })

  it('ログアウトボタンが表示されること', () => {
    renderWithProviders(<AppLayout />)
    expect(screen.getByRole('button', { name: 'ログアウト' })).toBeInTheDocument()
  })

  it('ログアウトで状態がクリアされること', async () => {
    renderWithProviders(<AppLayout />)
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: 'ログアウト' }))

    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    expect(mockNavigate).toHaveBeenCalledWith('/login')
  })
})
