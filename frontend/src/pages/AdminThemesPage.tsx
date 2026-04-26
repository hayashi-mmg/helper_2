import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Box,
  Button,
  HStack,
  Table,
  Text,
  VStack,
} from '@chakra-ui/react'
import { themesApi } from '@/api/themes'
import PageHeader from '@/components/ui/PageHeader'
import LoadingState from '@/components/ui/LoadingState'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import { toaster } from '@/components/ui/toaster'

/**
 * 管理者用テーマ一覧。
 * docs/admin_management_specification.md §12
 */
export default function AdminThemesPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [settingDefault, setSettingDefault] = useState<string | null>(null)

  const themesQuery = useQuery({
    queryKey: ['themes', 'admin-list'],
    queryFn: () => themesApi.list({ is_active: undefined }),
  })

  const toggleActiveMutation = useMutation({
    mutationFn: ({ themeKey, isActive }: { themeKey: string; isActive: boolean }) =>
      themesApi.update(themeKey, { is_active: isActive }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['themes'] })
      toaster.success({ title: '有効状態を更新しました' })
    },
    onError: () => toaster.error({ title: '更新に失敗しました' }),
  })

  const deleteMutation = useMutation({
    mutationFn: (themeKey: string) => themesApi.remove(themeKey),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['themes'] })
      setConfirmDelete(null)
      toaster.success({ title: 'テーマを削除しました' })
    },
    onError: (err: { response?: { data?: { detail?: { code?: string; message?: string } } } }) => {
      const code = err.response?.data?.detail?.code
      const msg = err.response?.data?.detail?.message ?? '削除に失敗しました'
      toaster.error({ title: msg, description: code })
      setConfirmDelete(null)
    },
  })

  const setDefaultMutation = useMutation({
    mutationFn: (themeKey: string) => themesApi.setDefault(themeKey),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['themes'] })
      setSettingDefault(null)
      toaster.success({ title: '既定テーマを変更しました' })
    },
    onError: () => {
      setSettingDefault(null)
      toaster.error({ title: '既定テーマの変更に失敗しました' })
    },
  })

  if (themesQuery.isLoading) return <LoadingState type="form" count={4} />

  const themes = themesQuery.data?.themes ?? []

  return (
    <Box>
      <PageHeader title="テーマ管理">
        <Button onClick={() => navigate('/admin/themes/new')} bg="brand.600" color="white" size="lg">
          新規登録
        </Button>
      </PageHeader>

      <Box bg="bg.card" borderRadius="xl" border="1px solid" borderColor="border.default" p={6}>
        <Table.Root size="md">
          <Table.Header>
            <Table.Row>
              <Table.ColumnHeader>キー</Table.ColumnHeader>
              <Table.ColumnHeader>名前</Table.ColumnHeader>
              <Table.ColumnHeader>種別</Table.ColumnHeader>
              <Table.ColumnHeader>状態</Table.ColumnHeader>
              <Table.ColumnHeader>操作</Table.ColumnHeader>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {themes.map((t) => (
              <Table.Row key={t.theme_key}>
                <Table.Cell>
                  <Text fontFamily="mono">{t.theme_key}</Text>
                </Table.Cell>
                <Table.Cell>
                  <VStack align="start" gap={0}>
                    <Text fontWeight="bold">{t.name}</Text>
                    {t.description && (
                      <Text fontSize="sm" color="text.secondary">
                        {t.description}
                      </Text>
                    )}
                  </VStack>
                </Table.Cell>
                <Table.Cell>{t.is_builtin ? '組込み' : 'カスタム'}</Table.Cell>
                <Table.Cell>{t.is_active ? '有効' : '無効'}</Table.Cell>
                <Table.Cell>
                  <HStack gap={2} wrap="wrap">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => navigate(`/admin/themes/${t.theme_key}/edit`)}
                    >
                      編集
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        toggleActiveMutation.mutate({
                          themeKey: t.theme_key,
                          isActive: !t.is_active,
                        })
                      }
                    >
                      {t.is_active ? '無効化' : '有効化'}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setSettingDefault(t.theme_key)}
                      disabled={!t.is_active}
                    >
                      既定に設定
                    </Button>
                    {!t.is_builtin && (
                      <Button
                        size="sm"
                        colorPalette="red"
                        variant="outline"
                        onClick={() => setConfirmDelete(t.theme_key)}
                      >
                        削除
                      </Button>
                    )}
                  </HStack>
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table.Root>
      </Box>

      {confirmDelete && (
        <ConfirmDialog
          open={!!confirmDelete}
          title="テーマを削除しますか"
          message={`${confirmDelete} を削除します。このテーマを選択中のユーザーはシステム既定に戻ります。`}
          onConfirm={() => deleteMutation.mutate(confirmDelete)}
          onClose={() => setConfirmDelete(null)}
          confirmLabel="削除"
        />
      )}

      {settingDefault && (
        <ConfirmDialog
          open={!!settingDefault}
          title="既定テーマを変更しますか"
          message={`${settingDefault} をシステム既定テーマに設定します。未ログイン画面および未設定ユーザーに即座に反映されます。`}
          onConfirm={() => setDefaultMutation.mutate(settingDefault)}
          onClose={() => setSettingDefault(null)}
          confirmLabel="設定"
          colorPalette="blue"
        />
      )}
    </Box>
  )
}
