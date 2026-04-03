import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ChakraProvider, defaultSystem } from '@chakra-ui/react'
import App from '../App'
import { useAuthStore } from '@/stores/auth'
import { mockSeniorUser } from '@/test-utils'

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
    })

    it('/ でダッシュボードが表示されること', () => {
      renderApp('/')
      expect(screen.getByText('DashboardPage')).toBeInTheDocument()
    })

    it('/recipes でレシピページが表示されること', () => {
      renderApp('/recipes')
      expect(screen.getByText('RecipesPage')).toBeInTheDocument()
    })

    it('/menu で献立ページが表示されること', () => {
      renderApp('/menu')
      expect(screen.getByText('MenuPage')).toBeInTheDocument()
    })

    it('/tasks で作業管理ページが表示されること', () => {
      renderApp('/tasks')
      expect(screen.getByText('TasksPage')).toBeInTheDocument()
    })

    it('/messages でメッセージページが表示されること', () => {
      renderApp('/messages')
      expect(screen.getByText('MessagesPage')).toBeInTheDocument()
    })

    it('/shopping で買い物ページが表示されること', () => {
      renderApp('/shopping')
      expect(screen.getByText('ShoppingPage')).toBeInTheDocument()
    })

    it('/profile でプロファイルページが表示されること', () => {
      renderApp('/profile')
      expect(screen.getByText('ProfilePage')).toBeInTheDocument()
    })
  })
})
