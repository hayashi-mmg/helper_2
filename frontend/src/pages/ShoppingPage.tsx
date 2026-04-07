import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Box, Button, Text, VStack, HStack, Badge, Textarea, Input,
} from '@chakra-ui/react'
import { getShoppingRequests, createShoppingRequest, updateShoppingItem } from '@/api/shopping'
import type { ShoppingRequest, ShoppingItem } from '@/types'
import PageHeader from '@/components/ui/PageHeader'
import FormField from '@/components/ui/FormField'
import Select from '@/components/ui/Select'
import LoadingState from '@/components/ui/LoadingState'
import EmptyState from '@/components/ui/EmptyState'
import { toaster } from '@/components/ui/toaster'
import { toLocalDateString } from '@/utils/date'

const ITEM_CATEGORIES = [
  { value: '食材', label: '食材' },
  { value: '調味料', label: '調味料' },
  { value: '日用品', label: '日用品' },
  { value: '医薬品', label: '医薬品' },
  { value: 'その他', label: 'その他' },
]

const STATUS_LABELS: Record<string, string> = {
  pending: '未購入',
  purchased: '購入済み',
  unavailable: '入手不可',
}
const STATUS_COLORS: Record<string, string> = {
  pending: 'orange',
  purchased: 'green',
  unavailable: 'red',
}
const REQUEST_STATUS_LABELS: Record<string, string> = {
  pending: '依頼中',
  accepted: '受付済',
  completed: '完了',
  cancelled: 'キャンセル',
}
const REQUEST_STATUS_COLORS: Record<string, string> = {
  pending: 'orange',
  accepted: 'blue',
  completed: 'green',
  cancelled: 'gray',
}

export default function ShoppingPage() {
  const queryClient = useQueryClient()
  const [filterStatus, setFilterStatus] = useState<string>('')
  const [showForm, setShowForm] = useState(false)
  const [seniorUserId, setSeniorUserId] = useState('')
  const [notes, setNotes] = useState('')
  const [items, setItems] = useState([{ item_name: '', category: 'その他', quantity: '', memo: '' }])

  const { data: requests, isLoading } = useQuery({
    queryKey: ['shopping', filterStatus],
    queryFn: () => getShoppingRequests(filterStatus || undefined),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      createShoppingRequest({
        senior_user_id: seniorUserId,
        request_date: toLocalDateString(),
        notes: notes || undefined,
        items: items.filter((i) => i.item_name.trim()).map((i) => ({
          item_name: i.item_name,
          category: i.category,
          quantity: i.quantity || undefined,
          memo: i.memo || undefined,
        })),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping'] })
      resetForm()
      toaster.success({ title: '買い物依頼を作成しました' })
    },
  })

  const updateItemMutation = useMutation({
    mutationFn: ({ itemId, status }: { itemId: string; status: string }) =>
      updateShoppingItem(itemId, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['shopping'] }),
  })

  const resetForm = () => {
    setShowForm(false)
    setSeniorUserId('')
    setNotes('')
    setItems([{ item_name: '', category: 'その他', quantity: '', memo: '' }])
  }

  const addItem = () => setItems([...items, { item_name: '', category: 'その他', quantity: '', memo: '' }])

  const updateItem = (idx: number, field: string, value: string) => {
    const updated = [...items]
    updated[idx] = { ...updated[idx], [field]: value }
    setItems(updated)
  }

  const removeItem = (idx: number) => {
    if (items.length > 1) setItems(items.filter((_, i) => i !== idx))
  }

  const filters = [
    { value: '', label: 'すべて' },
    { value: 'pending', label: '依頼中' },
    { value: 'accepted', label: '受付済' },
    { value: 'completed', label: '完了' },
    { value: 'cancelled', label: 'キャンセル' },
  ]

  return (
    <Box>
      <PageHeader title="買い物管理">
        <Button
          bg="brand.600"
          color="white"
          _hover={{ bg: 'brand.700' }}
          size="lg"
          onClick={() => { resetForm(); setShowForm(true) }}
        >
          + 新規依頼
        </Button>
      </PageHeader>

      {/* Status Filter */}
      <HStack mb={6} gap={2} flexWrap="wrap">
        {filters.map((f) => (
          <Button
            key={f.value}
            size="md"
            variant={filterStatus === f.value ? 'solid' : 'outline'}
            bg={filterStatus === f.value ? 'brand.600' : undefined}
            color={filterStatus === f.value ? 'white' : undefined}
            _hover={filterStatus === f.value ? { bg: 'brand.700' } : undefined}
            onClick={() => setFilterStatus(f.value)}
            cursor="pointer"
          >
            {f.label}
          </Button>
        ))}
      </HStack>

      {showForm && (
        <Box bg="bg.card" p={6} borderRadius="xl" border="1px solid" borderColor="border.default" shadow="sm" mb={6}>
          <Text fontSize="lg" fontWeight="bold" color="text.primary" mb={4}>新しい買い物依頼</Text>
          <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate() }}>
            <VStack gap={4} align="stretch">
              <FormField label="利用者ID" required>
                <Input
                  placeholder="利用者IDを入力"
                  value={seniorUserId}
                  onChange={(e) => setSeniorUserId(e.target.value)}
                  size="lg"
                  borderRadius="lg"
                  required
                />
              </FormField>
              <FormField label="備考">
                <Textarea
                  placeholder="備考を入力"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  borderRadius="lg"
                  rows={2}
                />
              </FormField>
              <Text fontSize="md" fontWeight="bold" color="text.primary">買い物リスト</Text>
              {items.map((item, idx) => (
                <HStack key={idx} gap={3} align="end">
                  <Box flex={2}>
                    <Input
                      placeholder="商品名"
                      value={item.item_name}
                      onChange={(e) => updateItem(idx, 'item_name', e.target.value)}
                      size="lg"
                      borderRadius="lg"
                      required
                    />
                  </Box>
                  <Box flex={1}>
                    <Select
                      value={item.category}
                      onChange={(v) => updateItem(idx, 'category', v)}
                      options={ITEM_CATEGORIES}
                    />
                  </Box>
                  <Box flex={1}>
                    <Input
                      placeholder="数量"
                      value={item.quantity}
                      onChange={(e) => updateItem(idx, 'quantity', e.target.value)}
                      size="lg"
                      borderRadius="lg"
                    />
                  </Box>
                  <Button
                    size="sm"
                    colorPalette="red"
                    variant="ghost"
                    onClick={() => removeItem(idx)}
                    cursor="pointer"
                    minW="36px"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </Button>
                </HStack>
              ))}
              <Button size="lg" variant="outline" onClick={addItem} cursor="pointer">
                + アイテム追加
              </Button>
              <HStack gap={3} pt={2}>
                <Button
                  type="submit"
                  bg="brand.600"
                  color="white"
                  _hover={{ bg: 'brand.700' }}
                  size="lg"
                  loading={createMutation.isPending}
                >
                  依頼を作成
                </Button>
                <Button size="lg" variant="outline" onClick={resetForm}>キャンセル</Button>
              </HStack>
            </VStack>
          </form>
        </Box>
      )}

      {isLoading ? (
        <LoadingState type="list" count={3} />
      ) : !requests?.length ? (
        <EmptyState message="買い物依頼はありません" icon="cart" />
      ) : (
        <VStack gap={4} align="stretch">
          {requests.map((req: ShoppingRequest) => (
            <Box
              key={req.id}
              bg="bg.card"
              p={6}
              borderRadius="xl"
              border="1px solid"
              borderColor="border.default"
            >
              <HStack justify="space-between" mb={4}>
                <HStack gap={3}>
                  <Text fontSize="md" fontWeight="bold" color="text.primary">
                    依頼日: {req.request_date}
                  </Text>
                  <Badge
                    colorPalette={REQUEST_STATUS_COLORS[req.status] || 'gray'}
                    variant="subtle"
                    fontSize="sm"
                    px={3}
                    py={1}
                  >
                    {REQUEST_STATUS_LABELS[req.status] || req.status}
                  </Badge>
                </HStack>
              </HStack>
              {req.notes && (
                <Text fontSize="sm" color="text.muted" mb={4}>備考: {req.notes}</Text>
              )}
              <VStack align="stretch" gap={2}>
                {req.items.map((item: ShoppingItem) => (
                  <HStack
                    key={item.id}
                    justify="space-between"
                    bg="bg.muted"
                    p={3}
                    borderRadius="lg"
                  >
                    <VStack align="start" gap={0}>
                      <Text fontSize="md" fontWeight="medium" color="text.primary">{item.item_name}</Text>
                      <HStack gap={2}>
                        <Text fontSize="sm" color="text.muted">{item.category}</Text>
                        {item.quantity && <Text fontSize="sm" color="text.muted">数量: {item.quantity}</Text>}
                      </HStack>
                    </VStack>
                    <HStack gap={2}>
                      <Badge
                        colorPalette={STATUS_COLORS[item.status] || 'gray'}
                        variant="subtle"
                        fontSize="sm"
                      >
                        {STATUS_LABELS[item.status] || item.status}
                      </Badge>
                      {item.status === 'pending' && (
                        <>
                          <Button
                            size="sm"
                            bg="success.500"
                            color="white"
                            _hover={{ bg: 'success.600' }}
                            onClick={() => updateItemMutation.mutate({ itemId: item.id, status: 'purchased' })}
                            cursor="pointer"
                          >
                            購入済み
                          </Button>
                          <Button
                            size="sm"
                            colorPalette="red"
                            variant="outline"
                            onClick={() => updateItemMutation.mutate({ itemId: item.id, status: 'unavailable' })}
                            cursor="pointer"
                          >
                            入手不可
                          </Button>
                        </>
                      )}
                    </HStack>
                  </HStack>
                ))}
              </VStack>
            </Box>
          ))}
        </VStack>
      )}
    </Box>
  )
}
