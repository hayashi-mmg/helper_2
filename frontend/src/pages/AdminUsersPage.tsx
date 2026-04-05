import { useState } from 'react'
import { Box, Button, Input, Text, VStack, HStack, Badge, Flex } from '@chakra-ui/react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  activateUser,
  createAdminUser,
  deactivateUser,
  getAdminUsers,
  resetPassword,
  updateAdminUser,
} from '@/api/admin'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import EmptyState from '@/components/ui/EmptyState'
import FormField from '@/components/ui/FormField'
import LoadingState from '@/components/ui/LoadingState'
import PageHeader from '@/components/ui/PageHeader'
import { toaster } from '@/components/ui/toaster'
import type { AdminUser } from '@/types'

interface ApiError {
  response?: { data?: { detail?: string } }
}

const roleOptions = [
  { value: '', label: 'すべて' },
  { value: 'senior', label: '利用者' },
  { value: 'helper', label: 'ヘルパー' },
  { value: 'care_manager', label: 'ケアマネ' },
  { value: 'system_admin', label: '管理者' },
]

const roleLabel: Record<string, string> = {
  senior: '利用者', helper: 'ヘルパー', care_manager: 'ケアマネ', system_admin: '管理者',
}
const roleColor: Record<string, string> = {
  senior: 'green', helper: 'blue', care_manager: 'purple', system_admin: 'red',
}

const emptyForm = {
  email: '', full_name: '', role: 'senior', phone: '', address: '',
  emergency_contact: '', medical_notes: '', care_level: '',
  certification_number: '',
}

export default function AdminUsersPage() {
  const [search, setSearch] = useState('')
  const [filterRole, setFilterRole] = useState('')
  const [page, setPage] = useState(1)
  const [showForm, setShowForm] = useState(false)
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [detailUser, setDetailUser] = useState<AdminUser | null>(null)
  const [confirmAction, setConfirmAction] = useState<{ type: string; user: AdminUser } | null>(null)
  const [tempPassword, setTempPassword] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'users', filterRole, search, page],
    queryFn: () => getAdminUsers({ role: filterRole || undefined, search: search || undefined, page, limit: 20 }),
    staleTime: 30_000,
  })

  const createMutation = useMutation({
    mutationFn: createAdminUser,
    onSuccess: (res) => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
      setShowForm(false)
      setForm(emptyForm)
      setTempPassword(res.temporary_password)
      toaster.create({ title: 'ユーザーを作成しました', type: 'success' })
    },
    onError: (err: ApiError) => {
      toaster.create({ title: err.response?.data?.detail ?? 'エラーが発生しました', type: 'error' })
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: Record<string, unknown> }) => updateAdminUser(id, updates),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
      setEditingUser(null)
      setShowForm(false)
      setForm(emptyForm)
      toaster.create({ title: 'ユーザーを更新しました', type: 'success' })
    },
    onError: (err: ApiError) => {
      toaster.create({ title: err.response?.data?.detail ?? 'エラーが発生しました', type: 'error' })
    },
  })

  const deactivateMutation = useMutation({
    mutationFn: deactivateUser,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
      setConfirmAction(null)
      setDetailUser(null)
      toaster.create({ title: 'ユーザーを無効化しました', type: 'success' })
    },
    onError: (err: ApiError) => {
      setConfirmAction(null)
      toaster.create({ title: err.response?.data?.detail ?? 'エラーが発生しました', type: 'error' })
    },
  })

  const activateMutation = useMutation({
    mutationFn: activateUser,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
      setConfirmAction(null)
      setDetailUser(null)
      toaster.create({ title: 'ユーザーを有効化しました', type: 'success' })
    },
  })

  const resetMutation = useMutation({
    mutationFn: resetPassword,
    onSuccess: (res) => {
      setConfirmAction(null)
      setTempPassword(res.temporary_password)
      toaster.create({ title: 'パスワードをリセットしました', type: 'success' })
    },
    onError: (err: ApiError) => {
      setConfirmAction(null)
      toaster.create({ title: err.response?.data?.detail ?? 'エラーが発生しました', type: 'error' })
    },
  })

  const handleSubmit = () => {
    const payload: Record<string, unknown> = {
      email: form.email,
      full_name: form.full_name,
      role: form.role,
      phone: form.phone || undefined,
      address: form.address || undefined,
    }
    if (form.role === 'senior') {
      payload.emergency_contact = form.emergency_contact || undefined
      payload.medical_notes = form.medical_notes || undefined
      if (form.care_level) payload.care_level = Number(form.care_level)
    }
    if (form.role === 'helper') {
      payload.certification_number = form.certification_number || undefined
    }

    if (editingUser) {
      updateMutation.mutate({ id: editingUser.id, updates: payload })
    } else {
      createMutation.mutate(payload as Parameters<typeof createAdminUser>[0])
    }
  }

  const openEdit = (user: AdminUser) => {
    setEditingUser(user)
    setForm({
      email: user.email,
      full_name: user.full_name,
      role: user.role,
      phone: user.phone ?? '',
      address: user.address ?? '',
      emergency_contact: user.emergency_contact ?? '',
      medical_notes: user.medical_notes ?? '',
      care_level: user.care_level?.toString() ?? '',
      certification_number: user.certification_number ?? '',
    })
    setShowForm(true)
    setDetailUser(null)
  }

  const users = data?.users ?? []
  const pagination = data?.pagination

  return (
    <VStack align="stretch" gap={6}>
      <PageHeader title="ユーザー管理">
        <Button colorPalette="blue" onClick={() => { setEditingUser(null); setForm(emptyForm); setShowForm(true) }}>
          新規作成
        </Button>
      </PageHeader>

      {/* フィルター */}
      <HStack gap={3} flexWrap="wrap">
        <Input
          placeholder="氏名・メールで検索..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          maxW="300px"
        />
        {roleOptions.map((r) => (
          <Button
            key={r.value}
            size="sm"
            variant={filterRole === r.value ? 'solid' : 'outline'}
            colorPalette={filterRole === r.value ? 'blue' : 'gray'}
            onClick={() => { setFilterRole(r.value); setPage(1) }}
          >
            {r.label}
          </Button>
        ))}
      </HStack>

      {/* ユーザー一覧 */}
      {isLoading ? (
        <LoadingState />
      ) : users.length === 0 ? (
        <EmptyState message="ユーザーが見つかりません" />
      ) : (
        <VStack align="stretch" gap={2}>
          {users.map((u) => (
            <Box
              key={u.id}
              bg="bg.card"
              p={4}
              borderRadius="lg"
              border="1px solid"
              borderColor="border.default"
              cursor="pointer"
              _hover={{ shadow: 'md' }}
              onClick={() => setDetailUser(u)}
            >
              <Flex justify="space-between" align="center">
                <HStack gap={3}>
                  <Badge colorPalette={roleColor[u.role] ?? 'gray'}>{roleLabel[u.role] ?? u.role}</Badge>
                  <Text fontWeight="bold" color="text.primary">{u.full_name}</Text>
                  <Text fontSize="sm" color="text.muted">{u.email}</Text>
                </HStack>
                <HStack gap={2}>
                  <Badge colorPalette={u.is_active ? 'green' : 'red'}>
                    {u.is_active ? '有効' : '無効'}
                  </Badge>
                </HStack>
              </Flex>
            </Box>
          ))}

          {pagination && pagination.total_pages > 1 && (
            <HStack justify="center" gap={2} mt={4}>
              <Button size="sm" disabled={!pagination.has_prev} onClick={() => setPage(page - 1)}>前へ</Button>
              <Text fontSize="sm" color="text.muted">{page} / {pagination.total_pages}</Text>
              <Button size="sm" disabled={!pagination.has_next} onClick={() => setPage(page + 1)}>次へ</Button>
            </HStack>
          )}
        </VStack>
      )}

      {/* 詳細モーダル */}
      {detailUser && (
        <Box position="fixed" top={0} left={0} w="100vw" h="100vh" bg="blackAlpha.500" zIndex={1000}
          onClick={(e) => { if (e.target === e.currentTarget) setDetailUser(null) }}>
          <Box position="absolute" top="50%" left="50%" transform="translate(-50%, -50%)"
            bg="bg.card" borderRadius="xl" p={6} w="500px" maxH="80vh" overflowY="auto" shadow="xl">
            <VStack align="stretch" gap={4}>
              <Flex justify="space-between" align="center">
                <HStack>
                  <Badge colorPalette={roleColor[detailUser.role] ?? 'gray'} size="lg">
                    {roleLabel[detailUser.role] ?? detailUser.role}
                  </Badge>
                  <Badge colorPalette={detailUser.is_active ? 'green' : 'red'}>
                    {detailUser.is_active ? '有効' : '無効'}
                  </Badge>
                </HStack>
                <Button size="sm" variant="ghost" onClick={() => setDetailUser(null)}>閉じる</Button>
              </Flex>
              <Text fontSize="xl" fontWeight="bold">{detailUser.full_name}</Text>
              <Text color="text.muted">{detailUser.email}</Text>
              {detailUser.phone && <Text>電話: {detailUser.phone}</Text>}
              {detailUser.address && <Text>住所: {detailUser.address}</Text>}
              {detailUser.care_level != null && <Text>要介護度: {detailUser.care_level}</Text>}
              {detailUser.certification_number && <Text>資格番号: {detailUser.certification_number}</Text>}
              {detailUser.last_login_at && <Text fontSize="sm" color="text.muted">最終ログイン: {new Date(detailUser.last_login_at).toLocaleString('ja-JP')}</Text>}
              <HStack gap={2} mt={2}>
                <Button size="sm" colorPalette="blue" onClick={() => openEdit(detailUser)}>編集</Button>
                {detailUser.is_active ? (
                  <Button size="sm" colorPalette="red" variant="outline"
                    onClick={() => setConfirmAction({ type: 'deactivate', user: detailUser })}>無効化</Button>
                ) : (
                  <Button size="sm" colorPalette="green" variant="outline"
                    onClick={() => setConfirmAction({ type: 'activate', user: detailUser })}>有効化</Button>
                )}
                <Button size="sm" variant="outline"
                  onClick={() => setConfirmAction({ type: 'reset', user: detailUser })}>パスワードリセット</Button>
              </HStack>
            </VStack>
          </Box>
        </Box>
      )}

      {/* 作成/編集モーダル */}
      {showForm && (
        <Box position="fixed" top={0} left={0} w="100vw" h="100vh" bg="blackAlpha.500" zIndex={1000}
          onClick={(e) => { if (e.target === e.currentTarget) { setShowForm(false); setEditingUser(null) } }}>
          <Box position="absolute" top="50%" left="50%" transform="translate(-50%, -50%)"
            bg="bg.card" borderRadius="xl" p={6} w="500px" maxH="80vh" overflowY="auto" shadow="xl">
            <VStack align="stretch" gap={4}>
              <Text fontSize="lg" fontWeight="bold">{editingUser ? 'ユーザーを編集' : '新しいユーザーを作成'}</Text>
              <FormField label="メールアドレス" required>
                <Input placeholder="email@example.com" value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </FormField>
              <FormField label="氏名" required>
                <Input placeholder="氏名を入力" value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
              </FormField>
              <FormField label="ロール" required>
                <HStack gap={2}>
                  {roleOptions.filter(r => r.value !== '').map(r => (
                    <Button key={r.value} size="sm"
                      variant={form.role === r.value ? 'solid' : 'outline'}
                      colorPalette={form.role === r.value ? 'blue' : 'gray'}
                      onClick={() => setForm({ ...form, role: r.value })}>
                      {r.label}
                    </Button>
                  ))}
                </HStack>
              </FormField>
              <FormField label="電話番号">
                <Input placeholder="090-0000-0000" value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })} />
              </FormField>
              {form.role === 'senior' && (
                <>
                  <FormField label="要介護度">
                    <Input type="number" min={1} max={5} value={form.care_level}
                      onChange={(e) => setForm({ ...form, care_level: e.target.value })} />
                  </FormField>
                  <FormField label="緊急連絡先">
                    <Input value={form.emergency_contact}
                      onChange={(e) => setForm({ ...form, emergency_contact: e.target.value })} />
                  </FormField>
                </>
              )}
              {form.role === 'helper' && (
                <FormField label="資格番号">
                  <Input value={form.certification_number}
                    onChange={(e) => setForm({ ...form, certification_number: e.target.value })} />
                </FormField>
              )}
              <HStack justify="flex-end" gap={2}>
                <Button variant="outline" onClick={() => { setShowForm(false); setEditingUser(null) }}>キャンセル</Button>
                <Button colorPalette="blue" onClick={handleSubmit}
                  disabled={!form.email || !form.full_name}>
                  {editingUser ? '更新' : '作成'}
                </Button>
              </HStack>
            </VStack>
          </Box>
        </Box>
      )}

      {/* 一時パスワード表示 */}
      {tempPassword && (
        <Box position="fixed" top={0} left={0} w="100vw" h="100vh" bg="blackAlpha.500" zIndex={1100}
          onClick={(e) => { if (e.target === e.currentTarget) setTempPassword(null) }}>
          <Box position="absolute" top="50%" left="50%" transform="translate(-50%, -50%)"
            bg="bg.card" borderRadius="xl" p={6} w="400px" shadow="xl">
            <VStack gap={4}>
              <Text fontSize="lg" fontWeight="bold">一時パスワード</Text>
              <Box bg="yellow.50" p={4} borderRadius="md" w="100%">
                <Text fontSize="lg" fontWeight="mono" textAlign="center" userSelect="all">{tempPassword}</Text>
              </Box>
              <Text fontSize="sm" color="text.muted">このパスワードを安全にユーザーに伝達してください。</Text>
              <Button onClick={() => setTempPassword(null)} w="100%">閉じる</Button>
            </VStack>
          </Box>
        </Box>
      )}

      {/* 確認ダイアログ */}
      {confirmAction && (
        <ConfirmDialog
          open={true}
          title={
            confirmAction.type === 'deactivate' ? 'ユーザーを無効化しますか？' :
            confirmAction.type === 'activate' ? 'ユーザーを有効化しますか？' :
            'パスワードをリセットしますか？'
          }
          message={`${confirmAction.user.full_name} (${confirmAction.user.email})`}
          confirmLabel={
            confirmAction.type === 'deactivate' ? '無効化' :
            confirmAction.type === 'activate' ? '有効化' : 'リセット'
          }
          onConfirm={() => {
            if (confirmAction.type === 'deactivate') deactivateMutation.mutate(confirmAction.user.id)
            else if (confirmAction.type === 'activate') activateMutation.mutate(confirmAction.user.id)
            else resetMutation.mutate(confirmAction.user.id)
          }}
          onClose={() => setConfirmAction(null)}
        />
      )}
    </VStack>
  )
}
