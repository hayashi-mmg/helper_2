import { describe, it, expect, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import DashboardPage from '../DashboardPage'
import { renderWithProviders, mockSeniorUser } from '@/test-utils'
import { useAuthStore } from '@/stores/auth'

describe('DashboardPage', () => {
  beforeEach(() => {
    useAuthStore.getState().setAuth('token', 'refresh', mockSeniorUser)
  })

  it('ユーザー名を含む挨拶が表示されること', () => {
    renderWithProviders(<DashboardPage />)
    expect(screen.getByText(/テスト太郎さん/)).toBeInTheDocument()
  })

  it('レシピ管理カードが表示されること', () => {
    renderWithProviders(<DashboardPage />)
    expect(screen.getByText('レシピ管理')).toBeInTheDocument()
    expect(screen.getByText('レシピの登録・編集')).toBeInTheDocument()
  })

  it('作業管理カードが表示されること', () => {
    renderWithProviders(<DashboardPage />)
    expect(screen.getByText('作業管理')).toBeInTheDocument()
  })

  it('メッセージカードが表示されること', () => {
    renderWithProviders(<DashboardPage />)
    expect(screen.getByText('メッセージ')).toBeInTheDocument()
  })

  it('3つのナビカードが表示されること', () => {
    renderWithProviders(<DashboardPage />)
    const links = screen.getAllByRole('link')
    expect(links.length).toBe(3)
  })

  it('各カードが正しいリンク先を持つこと', () => {
    renderWithProviders(<DashboardPage />)
    const links = screen.getAllByRole('link')
    const hrefs = links.map((l) => l.getAttribute('href'))
    expect(hrefs).toContain('/recipes')
    expect(hrefs).toContain('/tasks')
    expect(hrefs).toContain('/messages')
  })
})
