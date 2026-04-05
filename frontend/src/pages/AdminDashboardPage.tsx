import { Box, SimpleGrid, Text, VStack, HStack, Heading, Badge } from '@chakra-ui/react'
import { useQuery } from '@tanstack/react-query'
import { getDashboardStats } from '@/api/admin'
import LoadingState from '@/components/ui/LoadingState'
import PageHeader from '@/components/ui/PageHeader'

const roleLabelMap: Record<string, string> = {
  senior: '利用者',
  helper: 'ヘルパー',
  care_manager: 'ケアマネ',
  system_admin: '管理者',
}

function StatCard({ label, value, sub }: { label: string; value: number | string; sub?: string }) {
  return (
    <Box bg="bg.card" p={6} borderRadius="xl" shadow="sm" border="1px solid" borderColor="border.default">
      <Text fontSize="sm" color="text.muted" mb={1}>{label}</Text>
      <Text fontSize="3xl" fontWeight="bold" color="text.primary">{value}</Text>
      {sub && <Text fontSize="sm" color="text.secondary" mt={1}>{sub}</Text>}
    </Box>
  )
}

export default function AdminDashboardPage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['admin', 'dashboard'],
    queryFn: getDashboardStats,
    staleTime: 60_000,
  })

  if (isLoading) return <LoadingState />

  return (
    <VStack align="stretch" gap={6}>
      <PageHeader title="管理ダッシュボード" />

      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} gap={4}>
        <StatCard label="総ユーザー数" value={stats?.total_users ?? 0} />
        <StatCard label="アクティブ" value={stats?.active_users ?? 0} sub={`無効: ${String(stats?.inactive_users ?? 0)}`} />
        <StatCard label="今月の新規" value={stats?.new_users_this_month ?? 0} />
        <StatCard label="アクティブアサイン" value={stats?.active_assignments ?? 0} />
      </SimpleGrid>

      <SimpleGrid columns={{ base: 1, md: 2 }} gap={4}>
        <Box bg="bg.card" p={6} borderRadius="xl" shadow="sm" border="1px solid" borderColor="border.default">
          <Heading size="md" mb={4} color="text.primary">ロール別ユーザー数</Heading>
          <VStack align="stretch" gap={3}>
            {stats?.users_by_role && Object.entries(stats.users_by_role).map(([role, count]) => (
              <HStack key={role} justify="space-between">
                <HStack>
                  <Badge colorPalette={role === 'system_admin' ? 'red' : role === 'care_manager' ? 'purple' : role === 'helper' ? 'blue' : 'green'}>
                    {roleLabelMap[role] ?? role}
                  </Badge>
                </HStack>
                <Text fontWeight="bold" color="text.primary">{count}</Text>
              </HStack>
            ))}
          </VStack>
        </Box>

        <Box bg="bg.card" p={6} borderRadius="xl" shadow="sm" border="1px solid" borderColor="border.default">
          <Heading size="md" mb={4} color="text.primary">今週のアクティビティ</Heading>
          <VStack align="stretch" gap={3}>
            <HStack justify="space-between">
              <Text color="text.secondary">タスク完了数</Text>
              <Text fontWeight="bold" color="text.primary">{stats?.tasks_completed_this_week ?? 0}</Text>
            </HStack>
            <HStack justify="space-between">
              <Text color="text.secondary">本日のログイン数</Text>
              <Text fontWeight="bold" color="text.primary">{stats?.login_count_today ?? 0}</Text>
            </HStack>
          </VStack>
        </Box>
      </SimpleGrid>
    </VStack>
  )
}
