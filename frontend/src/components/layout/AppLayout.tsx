import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { Box, Flex, Heading, Button, HStack, Text } from '@chakra-ui/react'
import { useAuthStore } from '@/stores/auth'

const ADMIN_NAV_ITEMS = [
  {
    path: '/admin',
    label: '管理ダッシュ',
    icon: 'M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  },
  {
    path: '/admin/users',
    label: 'ユーザー管理',
    icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
  },
  {
    path: '/admin/assignments',
    label: 'アサイン管理',
    icon: 'M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4',
  },
]

const NAV_ITEMS = [
  {
    path: '/',
    label: 'ダッシュボード',
    icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6',
  },
  {
    path: '/recipes',
    label: 'レシピ',
    icon: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253',
  },
  {
    path: '/menu',
    label: '献立',
    icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01',
  },
  {
    path: '/tasks',
    label: '作業管理',
    icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
  },
  {
    path: '/messages',
    label: 'メッセージ',
    icon: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z',
  },
  {
    path: '/shopping',
    label: '買い物',
    icon: 'M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z',
  },
  {
    path: '/pantry',
    label: 'パントリー',
    icon: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4',
  },
]

function NavIcon({ d, active }: { d: string; active: boolean }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke={active ? '#0369A1' : '#64748B'}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={d} />
    </svg>
  )
}

export default function AppLayout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  return (
    <Box minH="100vh" bg="bg.page">
      {/* Header */}
      <Flex
        as="header"
        bg="brand.600"
        color="white"
        px={8}
        py={4}
        align="center"
        justify="space-between"
        shadow="md"
      >
        <Link to="/">
          <HStack gap={3}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            <Heading size="lg" fontWeight="bold">
              ヘルパー管理
            </Heading>
          </HStack>
        </Link>
        <HStack gap={4}>
          <Link to="/profile">
            <HStack
              gap={2}
              px={3}
              py={1.5}
              borderRadius="lg"
              cursor="pointer"
              _hover={{ bg: 'whiteAlpha.200' }}
              transition="background 0.2s"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
              <Text fontSize="md" fontWeight="medium">{user?.full_name}</Text>
            </HStack>
          </Link>
          <Button
            size="sm"
            variant="outline"
            color="white"
            borderColor="whiteAlpha.400"
            _hover={{ bg: 'whiteAlpha.200' }}
            onClick={handleLogout}
          >
            ログアウト
          </Button>
        </HStack>
      </Flex>

      {/* Navigation */}
      <Box
        as="nav"
        bg="bg.card"
        borderBottom="1px solid"
        borderColor="border.default"
        px={8}
        shadow="sm"
      >
        <HStack gap={1}>
          {(user?.role === 'system_admin' ? ADMIN_NAV_ITEMS : NAV_ITEMS).map((item) => {
            const active = isActive(item.path)
            return (
              <Link key={item.path} to={item.path}>
                <HStack
                  gap={2}
                  px={4}
                  py={3.5}
                  cursor="pointer"
                  borderBottom="3px solid"
                  borderColor={active ? 'brand.600' : 'transparent'}
                  color={active ? 'brand.600' : 'text.muted'}
                  fontWeight={active ? 'bold' : 'medium'}
                  _hover={{
                    color: 'brand.600',
                    bg: 'brand.50',
                  }}
                  transition="all 0.2s"
                >
                  <NavIcon d={item.icon} active={active} />
                  <Text fontSize="md">{item.label}</Text>
                </HStack>
              </Link>
            )
          })}
        </HStack>
      </Box>

      {/* Main Content */}
      <Box as="main" p={8} maxW="1280px" mx="auto">
        <Outlet />
      </Box>
    </Box>
  )
}
