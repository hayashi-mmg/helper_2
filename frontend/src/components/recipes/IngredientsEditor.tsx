import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Box, Button, Text, VStack, HStack, Input, Badge,
} from '@chakra-ui/react'
import { getRecipeIngredients, updateRecipeIngredients } from '@/api/recipe-ingredients'
import type { RecipeIngredientInput } from '@/types'
import Select from '@/components/ui/Select'
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

const CATEGORY_COLORS: Record<string, string> = {
  '野菜': 'green',
  '肉類': 'red',
  '魚介類': 'cyan',
  '卵・乳製品': 'orange',
  '調味料': 'purple',
  '穀類': 'yellow',
  'その他': 'gray',
}

interface Props {
  recipeId: string
  recipeName: string
}

export default function IngredientsEditor({ recipeId }: Props) {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [items, setItems] = useState<RecipeIngredientInput[]>([])

  const { data, isLoading } = useQuery({
    queryKey: ['recipe-ingredients', recipeId],
    queryFn: () => getRecipeIngredients(recipeId),
  })

  useEffect(() => {
    if (data) {
      setItems(data.ingredients.map((ing) => ({
        name: ing.name,
        quantity: ing.quantity || '',
        category: ing.category,
        sort_order: ing.sort_order,
      })))
    }
  }, [data])

  const saveMutation = useMutation({
    mutationFn: () =>
      updateRecipeIngredients(
        recipeId,
        items.filter((i) => i.name.trim()).map((i, idx) => ({ ...i, sort_order: idx + 1 })),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipe-ingredients', recipeId] })
      setEditing(false)
      toaster.success({ title: '食材を保存しました' })
    },
  })

  const addItem = () => setItems([...items, { name: '', quantity: '', category: 'その他', sort_order: items.length + 1 }])

  const updateItem = (idx: number, field: string, value: string) => {
    const updated = [...items]
    updated[idx] = { ...updated[idx], [field]: value }
    setItems(updated)
  }

  const removeItem = (idx: number) => setItems(items.filter((_, i) => i !== idx))

  if (isLoading) return <Text fontSize="md" color="text.muted">読み込み中...</Text>

  return (
    <Box mt={4} pt={4} borderTop="1px solid" borderColor="border.default">
      <HStack justify="space-between" mb={3}>
        <Text fontSize="md" fontWeight="bold" color="text.primary">
          構造化食材 ({data?.ingredients.length ?? 0}件)
        </Text>
        {!editing ? (
          <Button
            size="md"
            minH="44px"
            variant="outline"
            onClick={() => setEditing(true)}
            cursor="pointer"
            fontSize="md"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
            編集
          </Button>
        ) : (
          <HStack gap={2}>
            <Button
              size="md"
              minH="44px"
              bg="brand.600"
              color="white"
              _hover={{ bg: 'brand.700' }}
              onClick={() => saveMutation.mutate()}
              loading={saveMutation.isPending}
              cursor="pointer"
              fontSize="md"
            >
              保存
            </Button>
            <Button
              size="md"
              minH="44px"
              variant="outline"
              onClick={() => {
                setEditing(false)
                if (data) setItems(data.ingredients.map((i) => ({
                  name: i.name,
                  quantity: i.quantity || '',
                  category: i.category,
                  sort_order: i.sort_order,
                })))
              }}
              cursor="pointer"
              fontSize="md"
            >
              取消
            </Button>
          </HStack>
        )}
      </HStack>

      {editing ? (
        <VStack gap={3} align="stretch">
          {items.map((item, idx) => (
            <Box key={idx} bg="bg.muted" p={3} borderRadius="lg">
              <VStack gap={2} align="stretch">
                <HStack gap={2}>
                  <Input
                    placeholder="食材名"
                    value={item.name}
                    onChange={(e) => updateItem(idx, 'name', e.target.value)}
                    size="lg"
                    fontSize="md"
                    borderRadius="lg"
                    minH="44px"
                    flex={2}
                    bg="white"
                  />
                  <Input
                    placeholder="数量"
                    value={item.quantity || ''}
                    onChange={(e) => updateItem(idx, 'quantity', e.target.value)}
                    size="lg"
                    fontSize="md"
                    borderRadius="lg"
                    minH="44px"
                    flex={1}
                    bg="white"
                  />
                  <Button
                    size="md"
                    minH="44px"
                    minW="44px"
                    colorPalette="red"
                    variant="ghost"
                    onClick={() => removeItem(idx)}
                    cursor="pointer"
                    aria-label="食材を削除"
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </Button>
                </HStack>
                <Box>
                  <Select
                    value={item.category}
                    onChange={(v) => updateItem(idx, 'category', v)}
                    options={INGREDIENT_CATEGORIES}
                    size="lg"
                  />
                </Box>
              </VStack>
            </Box>
          ))}
          <Button
            size="md"
            minH="44px"
            variant="outline"
            onClick={addItem}
            cursor="pointer"
            fontSize="md"
            borderStyle="dashed"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            食材を追加
          </Button>
        </VStack>
      ) : (
        <VStack gap={2} align="stretch">
          {data?.ingredients.length ? (
            data.ingredients.map((ing) => (
              <HStack key={ing.id} gap={3} py={1.5}>
                <Badge
                  fontSize="sm"
                  colorPalette={CATEGORY_COLORS[ing.category] || 'gray'}
                  variant="subtle"
                  px={2}
                  py={0.5}
                  minW="60px"
                  textAlign="center"
                >
                  {ing.category}
                </Badge>
                <Text fontSize="md" color="text.primary" fontWeight="medium">{ing.name}</Text>
                {ing.quantity && <Text fontSize="md" color="text.muted">{ing.quantity}</Text>}
              </HStack>
            ))
          ) : (
            <Text fontSize="md" color="text.muted" fontStyle="italic">食材が登録されていません</Text>
          )}
        </VStack>
      )}
    </Box>
  )
}
