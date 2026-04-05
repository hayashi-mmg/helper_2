import { useState } from 'react'
import { Box, Button, Input, Text, VStack, HStack, Badge, Flex } from '@chakra-ui/react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createAssignment, deleteAssignment, getAdminUsers, getAssignments } from '@/api/admin'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import EmptyState from '@/components/ui/EmptyState'
import FormField from '@/components/ui/FormField'
import LoadingState from '@/components/ui/LoadingState'
import PageHeader from '@/components/ui/PageHeader'
import { toaster } from '@/components/ui/toaster'
import type { Assignment } from '@/types'

interface ApiError {
  response?: { data?: { detail?: string } }
}

const statusLabel: Record<string, string> = { active: 'アクティブ', inactive: '終了', pending: '保留' }
const statusColor: Record<string, string> = { active: 'green', inactive: 'gray', pending: 'orange' }
const dayLabels = ['', '月', '火', '水', '木', '金', '土', '日']

export default function AdminAssignmentsPage() {
  const [filterStatus, setFilterStatus] = useState('active')
  const [page, setPage] = useState(1)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ helper_id: '', senior_id: '', visit_frequency: '', notes: '' })
  const [deleteTarget, setDeleteTarget] = useState<Assignment | null>(null)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'assignments', filterStatus, page],
    queryFn: () => getAssignments({ status: filterStatus || undefined, page, limit: 20 }),
    staleTime: 30_000,
  })

  const { data: helpersData } = useQuery({
    queryKey: ['admin', 'users', 'helpers'],
    queryFn: () => getAdminUsers({ role: 'helper', is_active: true, limit: 100 }),
    enabled: showForm,
  })
  const { data: seniorsData } = useQuery({
    queryKey: ['admin', 'users', 'seniors'],
    queryFn: () => getAdminUsers({ role: 'senior', is_active: true, limit: 100 }),
    enabled: showForm,
  })

  const createMutation = useMutation({
    mutationFn: createAssignment,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'assignments'] })
      setShowForm(false)
      setForm({ helper_id: '', senior_id: '', visit_frequency: '', notes: '' })
      toaster.create({ title: 'アサインを作成しました', type: 'success' })
    },
    onError: (err: ApiError) => {
      toaster.create({ title: err.response?.data?.detail ?? 'エラーが発生しました', type: 'error' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteAssignment,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'assignments'] })
      setDeleteTarget(null)
      toaster.create({ title: 'アサインを終了しました', type: 'success' })
    },
  })

  const handleSubmit = () => {
    if (!form.helper_id || !form.senior_id) return
    createMutation.mutate({
      helper_id: form.helper_id,
      senior_id: form.senior_id,
      visit_frequency: form.visit_frequency || undefined,
      notes: form.notes || undefined,
    })
  }

  const assignments = data?.assignments ?? []
  const pagination = data?.pagination

  return (
    <VStack align="stretch" gap={6}>
      <PageHeader title="アサイン管理">
        <Button colorPalette="blue" onClick={() => setShowForm(true)}>新規アサイン</Button>
      </PageHeader>

      {/* フィルター */}
      <HStack gap={2}>
        {['', 'active', 'inactive', 'pending'].map((s) => (
          <Button key={s} size="sm"
            variant={filterStatus === s ? 'solid' : 'outline'}
            colorPalette={filterStatus === s ? 'blue' : 'gray'}
            onClick={() => { setFilterStatus(s); setPage(1) }}>
            {s === '' ? 'すべて' : statusLabel[s] ?? s}
          </Button>
        ))}
      </HStack>

      {/* アサイン一覧 */}
      {isLoading ? (
        <LoadingState />
      ) : assignments.length === 0 ? (
        <EmptyState message="アサインが見つかりません" />
      ) : (
        <VStack align="stretch" gap={2}>
          {assignments.map((a) => (
            <Box key={a.id} bg="bg.card" p={4} borderRadius="lg" border="1px solid" borderColor="border.default">
              <Flex justify="space-between" align="center">
                <VStack align="start" gap={1}>
                  <HStack gap={2}>
                    <Badge colorPalette={statusColor[a.status] ?? 'gray'}>{statusLabel[a.status] ?? a.status}</Badge>
                    {a.visit_frequency && <Text fontSize="sm" color="text.muted">{a.visit_frequency}</Text>}
                  </HStack>
                  <HStack gap={4}>
                    <VStack align="start" gap={0}>
                      <Text fontSize="xs" color="text.muted">ヘルパー</Text>
                      <Text fontWeight="bold">{a.helper.full_name}</Text>
                    </VStack>
                    <Text color="text.muted" fontSize="lg">→</Text>
                    <VStack align="start" gap={0}>
                      <Text fontSize="xs" color="text.muted">利用者</Text>
                      <Text fontWeight="bold">{a.senior.full_name}</Text>
                    </VStack>
                  </HStack>
                  {a.preferred_days && a.preferred_days.length > 0 && (
                    <Text fontSize="sm" color="text.muted">
                      訪問日: {a.preferred_days.map(d => dayLabels[d]).join('・')}
                    </Text>
                  )}
                </VStack>
                {a.status === 'active' && (
                  <Button size="sm" colorPalette="red" variant="outline"
                    onClick={() => setDeleteTarget(a)}>
                    終了
                  </Button>
                )}
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

      {/* 作成モーダル */}
      {showForm && (
        <Box position="fixed" top={0} left={0} w="100vw" h="100vh" bg="blackAlpha.500" zIndex={1000}
          onClick={(e) => { if (e.target === e.currentTarget) setShowForm(false) }}>
          <Box position="absolute" top="50%" left="50%" transform="translate(-50%, -50%)"
            bg="bg.card" borderRadius="xl" p={6} w="500px" shadow="xl">
            <VStack align="stretch" gap={4}>
              <Text fontSize="lg" fontWeight="bold">新しいアサインを作成</Text>
              <FormField label="ヘルパー" required>
                <select
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--chakra-colors-border-default, #e2e8f0)' }}
                  value={form.helper_id}
                  onChange={(e) => setForm({ ...form, helper_id: e.target.value })}>
                  <option value="">選択してください</option>
                  {helpersData?.users.map(u => (
                    <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>
                  ))}
                </select>
              </FormField>
              <FormField label="利用者" required>
                <select
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--chakra-colors-border-default, #e2e8f0)' }}
                  value={form.senior_id}
                  onChange={(e) => setForm({ ...form, senior_id: e.target.value })}>
                  <option value="">選択してください</option>
                  {seniorsData?.users.map(u => (
                    <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>
                  ))}
                </select>
              </FormField>
              <FormField label="訪問頻度">
                <Input placeholder="例: 週3回" value={form.visit_frequency}
                  onChange={(e) => setForm({ ...form, visit_frequency: e.target.value })} />
              </FormField>
              <FormField label="メモ">
                <Input placeholder="メモを入力" value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })} />
              </FormField>
              <HStack justify="flex-end" gap={2}>
                <Button variant="outline" onClick={() => setShowForm(false)}>キャンセル</Button>
                <Button colorPalette="blue" onClick={handleSubmit}
                  disabled={!form.helper_id || !form.senior_id}>
                  作成
                </Button>
              </HStack>
            </VStack>
          </Box>
        </Box>
      )}

      {/* 終了確認 */}
      {deleteTarget && (
        <ConfirmDialog
          open={true}
          title="アサインを終了しますか？"
          message={`${deleteTarget.helper.full_name} → ${deleteTarget.senior.full_name}`}
          confirmLabel="終了"
          onConfirm={() => deleteMutation.mutate(deleteTarget.id)}
          onClose={() => setDeleteTarget(null)}
        />
      )}
    </VStack>
  )
}
