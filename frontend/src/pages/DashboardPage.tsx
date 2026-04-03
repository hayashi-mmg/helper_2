import { Box, Heading, Text, SimpleGrid, HStack, VStack, Badge } from '@chakra-ui/react'
import { useAuthStore } from '@/stores/auth'
import { Link } from 'react-router-dom'

const ROLE_LABELS: Record<string, string> = {
  senior: '利用者',
  helper: 'ヘルパー',
  care_manager: 'ケアマネージャー',
}

const cards = [
  {
    title: 'レシピ管理',
    description: 'レシピの登録・編集・検索',
    path: '/recipes',
    color: 'success.500',
    bgHover: 'success.50',
    icon: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253',
  },
  {
    title: '献立管理',
    description: '週間献立の作成・管理',
    path: '/menu',
    color: 'brand.500',
    bgHover: 'brand.50',
    icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01',
  },
  {
    title: '作業管理',
    description: '本日の作業確認・完了報告',
    path: '/tasks',
    color: 'warn.500',
    bgHover: 'warn.50',
    icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
  },
  {
    title: 'メッセージ',
    description: 'ヘルパーとのやり取り',
    path: '/messages',
    color: 'brand.400',
    bgHover: 'brand.50',
    icon: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z',
  },
  {
    title: '買い物管理',
    description: '買い物依頼の作成・管理',
    path: '/shopping',
    color: 'success.600',
    bgHover: 'success.50',
    icon: 'M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z',
  },
  {
    title: 'プロファイル',
    description: '個人情報・設定の確認',
    path: '/profile',
    color: 'text.muted',
    bgHover: 'bg.muted',
    icon: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z',
  },
]

function CardIcon({ d, color }: { d: string; color: string }) {
  const colorMap: Record<string, string> = {
    'success.500': '#22C55E',
    'success.600': '#16A34A',
    'brand.500': '#0EA5E9',
    'brand.400': '#38BDF8',
    'warn.500': '#F59E0B',
    'text.muted': '#64748B',
  }

  return (
    <Box
      w="48px"
      h="48px"
      borderRadius="xl"
      display="flex"
      alignItems="center"
      justifyContent="center"
      bg={color.replace('.500', '.50').replace('.600', '.50').replace('.400', '.50').replace('text.muted', 'bg.muted')}
    >
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke={colorMap[color] || '#64748B'}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d={d} />
      </svg>
    </Box>
  )
}

export default function DashboardPage() {
  const user = useAuthStore((state) => state.user)

  return (
    <Box>
      {/* Welcome Section */}
      <Box
        bg="bg.card"
        borderRadius="2xl"
        border="1px solid"
        borderColor="border.default"
        p={8}
        mb={8}
      >
        <HStack justify="space-between" align="center">
          <VStack align="start" gap={2}>
            <Heading size="2xl" color="text.primary" fontWeight="bold">
              こんにちは、{user?.full_name}さん
            </Heading>
            <Text fontSize="md" color="text.muted">
              今日もお疲れさまです。ご確認ください。
            </Text>
          </VStack>
          <Badge
            bg="brand.50"
            color="brand.700"
            fontSize="md"
            px={4}
            py={2}
            borderRadius="lg"
            fontWeight="semibold"
          >
            {ROLE_LABELS[user?.role || ''] || user?.role}
          </Badge>
        </HStack>
      </Box>

      {/* Navigation Cards */}
      <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={6}>
        {cards.map((card) => (
          <Link key={card.path} to={card.path}>
            <Box
              p={6}
              bg="bg.card"
              borderRadius="xl"
              border="1px solid"
              borderColor="border.default"
              _hover={{
                borderColor: 'border.hover',
                shadow: 'md',
                transform: 'translateY(-2px)',
              }}
              transition="all 0.2s"
              cursor="pointer"
              h="full"
            >
              <VStack align="start" gap={4}>
                <CardIcon d={card.icon} color={card.color} />
                <Box>
                  <Heading size="lg" color="text.primary" mb={1} fontWeight="semibold">
                    {card.title}
                  </Heading>
                  <Text fontSize="md" color="text.muted">
                    {card.description}
                  </Text>
                </Box>
              </VStack>
            </Box>
          </Link>
        ))}
      </SimpleGrid>
    </Box>
  )
}
