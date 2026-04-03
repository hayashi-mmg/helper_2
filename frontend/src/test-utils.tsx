import { ReactElement } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ChakraProvider, defaultSystem } from '@chakra-ui/react'

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })
}

interface WrapperOptions {
  initialEntries?: string[]
}

export function createWrapper(options: WrapperOptions = {}) {
  const queryClient = createTestQueryClient()
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <MemoryRouter initialEntries={options.initialEntries || ['/']}>
        <QueryClientProvider client={queryClient}>
          <ChakraProvider value={defaultSystem}>
            {children}
          </ChakraProvider>
        </QueryClientProvider>
      </MemoryRouter>
    )
  }
}

export function renderWithProviders(
  ui: ReactElement,
  options: WrapperOptions & Omit<RenderOptions, 'wrapper'> = {},
) {
  const { initialEntries, ...renderOptions } = options
  return render(ui, {
    wrapper: createWrapper({ initialEntries }),
    ...renderOptions,
  })
}

// Mock user data
export const mockSeniorUser = {
  id: 'user-1',
  email: 'senior@test.com',
  full_name: 'テスト太郎',
  role: 'senior' as const,
}

export const mockHelperUser = {
  id: 'user-2',
  email: 'helper@test.com',
  full_name: 'ヘルパー花子',
  role: 'helper' as const,
}
