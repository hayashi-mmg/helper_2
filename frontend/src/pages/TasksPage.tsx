import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Box, Text, VStack, Badge, HStack, Button, Input, Textarea } from '@chakra-ui/react'
import { getTodayTasks, createTask, updateTask, deleteTask } from '@/api/tasks'
import { useAuthStore } from '@/stores/auth'
import PageHeader from '@/components/ui/PageHeader'
import FormField from '@/components/ui/FormField'
import Select from '@/components/ui/Select'
import LoadingState from '@/components/ui/LoadingState'
import EmptyState from '@/components/ui/EmptyState'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import { toaster } from '@/components/ui/toaster'

const priorityColor: Record<string, string> = {
  high: 'red',
  medium: 'orange',
  low: 'green',
}

const statusLabel: Record<string, string> = {
  pending: '未着手',
  in_progress: '進行中',
  completed: '完了',
  cancelled: 'キャンセル',
}

const statusColor: Record<string, string> = {
  pending: 'gray',
  in_progress: 'blue',
  completed: 'green',
  cancelled: 'red',
}

const taskTypeLabel: Record<string, string> = {
  cooking: '料理',
  cleaning: '掃除',
  shopping: '買い物',
  special: '特別',
}

const taskTypes = [
  { value: 'cooking', label: '料理' },
  { value: 'cleaning', label: '掃除' },
  { value: 'shopping', label: '買い物' },
  { value: 'special', label: '特別' },
]

const priorities = [
  { value: 'high', label: '高' },
  { value: 'medium', label: '中' },
  { value: 'low', label: '低' },
]

const emptyForm = {
  title: '',
  description: '',
  task_type: 'cooking',
  priority: 'medium',
  estimated_minutes: '',
  scheduled_date: new Date().toISOString().split('T')[0],
}

export default function TasksPage() {
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0])
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const user = useAuthStore((state) => state.user)
  const queryClient = useQueryClient()

  const { data: tasks, isLoading } = useQuery({
    queryKey: ['tasks-today', selectedDate],
    queryFn: () => getTodayTasks({ date: selectedDate }),
  })

  const createMutation = useMutation({
    mutationFn: () => createTask({
      senior_user_id: user!.id,
      title: form.title,
      description: form.description || undefined,
      task_type: form.task_type,
      priority: form.priority,
      estimated_minutes: form.estimated_minutes ? Number(form.estimated_minutes) : undefined,
      scheduled_date: form.scheduled_date,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks-today'] })
      resetForm()
      toaster.success({ title: '作業を追加しました' })
    },
  })

  const updateMutation = useMutation({
    mutationFn: () => updateTask(editingId!, {
      title: form.title,
      description: form.description || undefined,
      task_type: form.task_type,
      priority: form.priority,
      estimated_minutes: form.estimated_minutes ? Number(form.estimated_minutes) : undefined,
      scheduled_date: form.scheduled_date,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks-today'] })
      resetForm()
      toaster.success({ title: '作業を更新しました' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteTask(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks-today'] })
      setDeleteTarget(null)
      toaster.success({ title: '作業を削除しました' })
    },
  })

  const resetForm = () => {
    setForm({ ...emptyForm, scheduled_date: selectedDate })
    setShowForm(false)
    setEditingId(null)
  }

  const startEdit = (task: { id: string; title: string; description?: string; task_type: string; priority: string; estimated_minutes?: number; scheduled_date: string }) => {
    setForm({
      title: task.title,
      description: task.description || '',
      task_type: task.task_type,
      priority: task.priority,
      estimated_minutes: task.estimated_minutes ? String(task.estimated_minutes) : '',
      scheduled_date: task.scheduled_date,
    })
    setEditingId(task.id)
    setShowForm(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingId) {
      updateMutation.mutate()
    } else {
      createMutation.mutate()
    }
  }

  const isSaving = createMutation.isPending || updateMutation.isPending
  const visibleTasks = tasks?.filter((t) => t.status !== 'cancelled')

  return (
    <Box>
      <PageHeader title="作業管理">
        <Button
          bg="brand.600"
          color="white"
          _hover={{ bg: 'brand.700' }}
          size="lg"
          onClick={() => { resetForm(); setShowForm(true) }}
        >
          + 新規追加
        </Button>
      </PageHeader>

      <Box mb={6}>
        <FormField label="表示日付">
          <Input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            size="lg"
            borderRadius="lg"
            maxW="250px"
            bg="bg.card"
          />
        </FormField>
      </Box>

      {showForm && (
        <Box bg="bg.card" p={6} borderRadius="xl" border="1px solid" borderColor="border.default" shadow="sm" mb={6}>
          <Text fontSize="lg" fontWeight="bold" color="text.primary" mb={4}>
            {editingId ? '作業を編集' : '新しい作業を追加'}
          </Text>
          <form onSubmit={handleSubmit}>
            <VStack gap={4} align="stretch">
              <FormField label="作業名" required>
                <Input
                  placeholder="作業名を入力"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  size="lg"
                  borderRadius="lg"
                  required
                />
              </FormField>
              <FormField label="説明">
                <Textarea
                  placeholder="説明を入力"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  borderRadius="lg"
                  rows={3}
                />
              </FormField>
              <HStack gap={4}>
                <Box flex={1}>
                  <FormField label="種類">
                    <Select value={form.task_type} onChange={(v) => setForm({ ...form, task_type: v })} options={taskTypes} />
                  </FormField>
                </Box>
                <Box flex={1}>
                  <FormField label="優先度">
                    <Select value={form.priority} onChange={(v) => setForm({ ...form, priority: v })} options={priorities} />
                  </FormField>
                </Box>
              </HStack>
              <HStack gap={4}>
                <Box flex={1}>
                  <FormField label="予定時間（分）">
                    <Input
                      type="number"
                      placeholder="分"
                      value={form.estimated_minutes}
                      onChange={(e) => setForm({ ...form, estimated_minutes: e.target.value })}
                      size="lg"
                      borderRadius="lg"
                      min={1}
                    />
                  </FormField>
                </Box>
                <Box flex={1}>
                  <FormField label="予定日" required>
                    <Input
                      type="date"
                      value={form.scheduled_date}
                      onChange={(e) => setForm({ ...form, scheduled_date: e.target.value })}
                      size="lg"
                      borderRadius="lg"
                      required
                    />
                  </FormField>
                </Box>
              </HStack>
              <HStack gap={3} pt={2}>
                <Button
                  type="submit"
                  bg="brand.600"
                  color="white"
                  _hover={{ bg: 'brand.700' }}
                  size="lg"
                  loading={isSaving}
                >
                  {editingId ? '更新' : '追加'}
                </Button>
                <Button size="lg" variant="outline" onClick={resetForm}>
                  キャンセル
                </Button>
              </HStack>
            </VStack>
          </form>
        </Box>
      )}

      {isLoading ? (
        <LoadingState type="list" count={4} />
      ) : visibleTasks && visibleTasks.length > 0 ? (
        <VStack gap={4} align="stretch">
          {visibleTasks.map((task) => (
            <Box
              key={task.id}
              p={6}
              bg="bg.card"
              borderRadius="xl"
              border="1px solid"
              borderColor="border.default"
              _hover={{ borderColor: 'border.hover', shadow: 'sm' }}
              transition="all 0.2s"
            >
              <HStack justify="space-between" mb={2}>
                <Text fontSize="lg" fontWeight="bold" color="text.primary">
                  {task.title}
                </Text>
                <Badge colorPalette={priorityColor[task.priority]} variant="subtle" fontSize="sm" px={3} py={1}>
                  優先度: {task.priority === 'high' ? '高' : task.priority === 'medium' ? '中' : '低'}
                </Badge>
              </HStack>
              {task.description && (
                <Text fontSize="md" color="text.secondary" mb={3}>
                  {task.description}
                </Text>
              )}
              <HStack gap={3} mb={3} flexWrap="wrap">
                <Badge variant="subtle">{taskTypeLabel[task.task_type] || task.task_type}</Badge>
                <Badge colorPalette={statusColor[task.status] || 'gray'} variant="subtle">
                  {statusLabel[task.status] || task.status}
                </Badge>
                {task.estimated_minutes && (
                  <HStack gap={1} color="text.muted" fontSize="sm">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10" />
                      <polyline points="12 6 12 12 16 14" />
                    </svg>
                    <Text>約{task.estimated_minutes}分</Text>
                  </HStack>
                )}
              </HStack>
              <HStack gap={2}>
                <Button size="sm" variant="outline" onClick={() => startEdit(task)} cursor="pointer">
                  編集
                </Button>
                <Button size="sm" colorPalette="red" variant="ghost" onClick={() => setDeleteTarget(task.id)} cursor="pointer">
                  削除
                </Button>
              </HStack>
            </Box>
          ))}
        </VStack>
      ) : (
        <EmptyState message="この日の作業はありません" icon="calendar" />
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget)}
        title="作業を削除"
        message="この作業を削除しますか？この操作は取り消せません。"
        loading={deleteMutation.isPending}
      />
    </Box>
  )
}
