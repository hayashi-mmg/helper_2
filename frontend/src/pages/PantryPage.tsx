import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Box, Button, Text, VStack, HStack, Badge, Input,
} from '@chakra-ui/react'
import { getPantryItems, updatePantryItems, deletePantryItem } from '@/api/pantry'
import type { PantryItem } from '@/types'
import PageHeader from '@/components/ui/PageHeader'
import FormField from '@/components/ui/FormField'
import Select from '@/components/ui/Select'
import LoadingState from '@/components/ui/LoadingState'
import EmptyState from '@/components/ui/EmptyState'
import { toaster } from '@/components/ui/toaster'

const INGREDIENT_CATEGORIES = [
  { value: '野菜', label: '野菜' },
  { value: '肉類', label: '肉類' },
  { value: '魚介類', label: '魚介類' },
  { value: '卵・乳製品', label: '卵・乳製品' },
  { value: '調味料', label: '調味料' },
  { value: '穀類', label: '穀類' },
  { value: 'その他', label: 'その他' },
]

export default function PantryPage() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [newName, setNewName] = useState('')
  const [newCategory, setNewCategory] = useState('その他')

  const { data, isLoading } = useQuery({
    queryKey: ['pantry'],
    queryFn: () => getPantryItems(),
  })

  const addMutation = useMutation({
    mutationFn: () =>
      updatePantryItems([{ name: newName.trim(), category: newCategory, is_available: true }]),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pantry'] })
      setNewName('')
      setNewCategory('その他')
      setShowForm(false)
      toaster.success({ title: '食材を追加しました' })
    },
  })

  const toggleMutation = useMutation({
    mutationFn: (item: PantryItem) =>
      updatePantryItems([{ name: item.name, category: item.category, is_available: !item.is_available }]),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['pantry'] }),
  })

  const removeMutation = useMutation({
    mutationFn: (itemId: string) => deletePantryItem(itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pantry'] })
      toaster.success({ title: '食材を削除しました' })
    },
  })

  const availableCount = data?.pantry_items.filter((i) => i.is_available).length ?? 0

  return (
    <Box>
      <PageHeader title="パントリー（在庫管理）">
        <Button
          bg="brand.600"
          color="white"
          _hover={{ bg: 'brand.700' }}
          size="lg"
          onClick={() => setShowForm(true)}
        >
          + 食材を追加
        </Button>
      </PageHeader>

      <Text fontSize="md" color="text.secondary" mb={6}>
        手元にある食材を登録しておくと、献立から買い物リストを生成する際に自動的に除外されます。
      </Text>

      {/* Summary */}
      <HStack mb={6} gap={4}>
        <Badge bg="brand.50" color="brand.700" fontSize="sm" px={4} py={2} borderRadius="lg">
          全{data?.total ?? 0}件
        </Badge>
        <Badge bg="success.50" color="success.700" fontSize="sm" px={4} py={2} borderRadius="lg">
          在庫あり: {availableCount}件
        </Badge>
      </HStack>

      {/* Add Form */}
      {showForm && (
        <Box bg="bg.card" p={6} borderRadius="xl" border="1px solid" borderColor="border.default" shadow="sm" mb={6}>
          <Text fontSize="lg" fontWeight="bold" color="text.primary" mb={4}>食材を追加</Text>
          <form onSubmit={(e) => { e.preventDefault(); if (newName.trim()) addMutation.mutate() }}>
            <HStack gap={4} align="end">
              <Box flex={2}>
                <FormField label="食材名" required>
                  <Input
                    placeholder="例: しょうゆ"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    size="lg"
                    borderRadius="lg"
                    required
                  />
                </FormField>
              </Box>
              <Box flex={1}>
                <FormField label="カテゴリ">
                  <Select
                    value={newCategory}
                    onChange={setNewCategory}
                    options={INGREDIENT_CATEGORIES}
                  />
                </FormField>
              </Box>
              <HStack gap={2} pb={1}>
                <Button type="submit" bg="brand.600" color="white" _hover={{ bg: 'brand.700' }} size="lg" loading={addMutation.isPending}>
                  追加
                </Button>
                <Button size="lg" variant="outline" onClick={() => setShowForm(false)}>取消</Button>
              </HStack>
            </HStack>
          </form>
        </Box>
      )}

      {/* List */}
      {isLoading ? (
        <LoadingState type="list" count={5} />
      ) : !data?.pantry_items.length ? (
        <EmptyState message="パントリーに食材が登録されていません" icon="inbox" />
      ) : (
        <VStack gap={2} align="stretch">
          {data.pantry_items.map((item: PantryItem) => (
            <HStack
              key={item.id}
              bg="bg.card"
              p={4}
              borderRadius="xl"
              border="1px solid"
              borderColor="border.default"
              justify="space-between"
              opacity={item.is_available ? 1 : 0.5}
            >
              <HStack gap={3}>
                <Text
                  fontSize="md"
                  fontWeight="medium"
                  color="text.primary"
                  textDecoration={item.is_available ? 'none' : 'line-through'}
                >
                  {item.name}
                </Text>
                <Badge colorPalette="blue" variant="subtle" fontSize="xs">{item.category}</Badge>
              </HStack>
              <HStack gap={2}>
                <Button
                  size="sm"
                  variant={item.is_available ? 'solid' : 'outline'}
                  bg={item.is_available ? 'success.500' : undefined}
                  color={item.is_available ? 'white' : undefined}
                  _hover={item.is_available ? { bg: 'success.600' } : undefined}
                  onClick={() => toggleMutation.mutate(item)}
                  cursor="pointer"
                >
                  {item.is_available ? '在庫あり' : '在庫なし'}
                </Button>
                <Button
                  size="sm"
                  colorPalette="red"
                  variant="ghost"
                  onClick={() => removeMutation.mutate(item.id)}
                  cursor="pointer"
                >
                  削除
                </Button>
              </HStack>
            </HStack>
          ))}
        </VStack>
      )}
    </Box>
  )
}
