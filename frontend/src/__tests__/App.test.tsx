import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ChakraProvider, defaultSystem } from '@chakra-ui/react'
import App from '../App'
import { useAuthStore } from '@/stores/auth'
import { mockSeniorUser } from '@/test-utils'

// API モック
const mockGetProfile = vi.fn()
vi.mock('@/api/users', () => ({
  getProfile: (...args: unknown[]) => mockGetProfile(...args),
}))

// ページモック（重い依存を避ける）
vi.mock('@/pages/LoginPage', () => ({ default: () => <div>LoginPage</div> }))
vi.mock('@/pages/DashboardPage', () => ({ default: () => <div>DashboardPage</div> }))
vi.mock('@/pages/RecipesPage', () => ({ default: () => <div>RecipesPage</div> }))
vi.mock('@/pages/MenuPage', () => ({ default: () => <div>MenuPage</div> }))
vi.mock('@/pages/TasksPage', () => ({ default: () => <div>TasksPage</div> }))
vi.mock('@/pages/MessagesPage', () => ({ default: () => <div>MessagesPage</div> }))
vi.mock('@/pages/ShoppingPage', () => ({ default: () => <div>ShoppingPage</div> }))
vi.mock('@/pages/ProfilePage', () => ({ default: () => <div>ProfilePage</div> }))

function renderApp(initialEntry: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <QueryClientProvider client={queryClient}>
        <ChakraProvider value={defaultSystem}>
          <App />
        </ChakraProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('App ルーティング', () => {
  describe('未認証', () => {
    beforeEach(() => {
      useAuthStore.getState().logout()
    })

    it('/login でログインページが表示されること', () => {
      renderApp('/login')
      expect(screen.getByText('LoginPage')).toBeInTheDocument()
    })

    it('/ にアクセスするとログインにリダイレクトされること', () => {
      renderApp('/')
      expect(screen.getByText('LoginPage')).toBeInTheDocument()
    })

    it('/recipes にアクセスするとログインにリダイレクトされること', () => {
      renderApp('/recipes')
      expect(screen.getByText('LoginPage')).toBeInTheDocument()
    })
  })

  describe('認証済み', () => {
    beforeEach(() => {
      useAuthStore.getState().setAuth('token', 'refresh', mockSeniorUser)
      mockGetProfile.mockResolvedValue({ id: '1', email: 'test@test.com', full_name: 'Test', role: 'senior' })
    })

    it('/ でダッシュボードが表示されること', async () => {
      renderApp('/')
      expect(await screen.findByText('DashboardPage')).toBeInTheDocument()
    })

    it('/recipes でレシピページが表示されること', async () => {
      renderApp('/recipes')
      expect(await screen.findByText('RecipesPage')).toBeInTheDocument()
    })

    it('/menu で献立ページが表示されること', async () => {
      renderApp('/menu')
      expect(await screen.findByText('MenuPage')).toBeInTheDocument()
    })

    it('/tasks で作業管理ページが表示されること', async () => {
      renderApp('/tasks')
      expect(await screen.findByText('TasksPage')).toBeInTheDocument()
    })

    it('/messages でメッセージページが表示されること', async () => {
      renderApp('/messages')
      expect(await screen.findByText('MessagesPage')).toBeInTheDocument()
    })

    it('/shopping で買い物ページが表示されること', async () => {
      renderApp('/shopping')
      expect(await screen.findByText('ShoppingPage')).toBeInTheDocument()
    })

    it('/profile でプロファイルページが表示されること', async () => {
      renderApp('/profile')
      expect(await screen.findByText('ProfilePage')).toBeInTheDocument()
    })
  })

  describe('トークン無効', () => {
    beforeEach(() => {
      useAuthStore.getState().setAuth('expired-token', 'refresh', mockSeniorUser)
      mockGetProfile.mockRejectedValue({ response: { status: 401 } })
    })

    it('無効なトークンでログインにリダイレクトされること', async () => {
      renderApp('/')
      await waitFor(() => {
        expect(screen.getByText('LoginPage')).toBeInTheDocument()
      })
    })
  })
})
