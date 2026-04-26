import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Box, Text, SimpleGrid, Spinner } from '@chakra-ui/react'
import { themesApi } from '@/api/themes'
import { preferencesApi } from '@/api/preferences'
import { useUIStore } from '@/stores/ui'
import { toaster } from '@/components/ui/toaster'
import ThemeCard from './ThemeCard'

/**
 * プロファイル画面のテーマ選択セクション。
 * 仕様: docs/theme_system_specification.md §5、docs/frontend_implementation_plan.md §3.1
 */
export default function ThemeSelector() {
  const queryClient = useQueryClient()
  const themeId = useUIStore((s) => s.themeId)
  const setPendingThemeId = useUIStore((s) => s.setPendingThemeId)
  const pendingThemeId = useUIStore((s) => s.pendingThemeId)

  const themesQuery = useQuery({
    queryKey: ['themes', 'list'],
    queryFn: () => themesApi.list({ is_active: true }),
    staleTime: 5 * 60 * 1000,
  })

  const mutation = useMutation({
    mutationFn: (newThemeId: string) =>
      preferencesApi.updateMine({ theme_id: newThemeId }),
    onMutate: (newThemeId) => {
      setPendingThemeId(newThemeId)
    },
    onSuccess: async (_data, newThemeId) => {
      await queryClient.invalidateQueries({ queryKey: ['preferences', 'me'] })
      await queryClient.invalidateQueries({ queryKey: ['themes', newThemeId] })
      setPendingThemeId(null)
      toaster.success({ title: 'テーマを変更しました' })
    },
    onError: () => {
      setPendingThemeId(null)
      toaster.error({ title: 'テーマの変更に失敗しました' })
    },
  })

  const activeId = pendingThemeId ?? themeId ?? 'standard'

  if (themesQuery.isLoading) {
    return (
      <Box p={4} textAlign="center">
        <Spinner />
      </Box>
    )
  }

  if (themesQuery.isError || !themesQuery.data) {
    return (
      <Text color="danger.500" role="alert">
        テーマ一覧を取得できませんでした
      </Text>
    )
  }

  return (
    <Box role="radiogroup" aria-labelledby="theme-heading">
      <SimpleGrid columns={{ base: 1, md: 2 }} gap={4}>
        {themesQuery.data.themes.map((t) => (
          <ThemeCard
            key={t.theme_key}
            summary={t}
            selected={activeId === t.theme_key}
            onSelect={() => mutation.mutate(t.theme_key)}
          />
        ))}
      </SimpleGrid>
    </Box>
  )
}
