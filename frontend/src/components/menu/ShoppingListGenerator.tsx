import { useState, useMemo } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Box, Button, Text, VStack, HStack, Badge, Input,
} from '@chakra-ui/react'
import { generateFromMenu, toggleExclude } from '@/api/shopping'
import type { GenerateFromMenuResponse, GeneratedItem } from '@/types'
import { toaster } from '@/components/ui/toaster'

interface Props {
  weekStart: string
  hasRecipes: boolean
}

const CATEGORY_ORDER = ['野菜', '肉類', '魚介類', '卵・乳製品', '穀類', '調味料', 'その他']

export default function ShoppingListGenerator({ weekStart, hasRecipes }: Props) {
  const queryClient = useQueryClient()
  const [result, setResult] = useState<GenerateFromMenuResponse | null>(null)
  const [notes, setNotes] = useState('')
  const [showForm, setShowForm] = useState(false)

  const generateMutation = useMutation({
    mutationFn: () =>
      generateFromMenu({
        week_start: weekStart,
        notes: notes || undefined,
      }),
    onSuccess: (data) => {
      setResult(data)
      queryClient.invalidateQueries({ queryKey: ['shopping'] })
      toaster.success({ title: '買い物リストを生成しました' })
    },
    onError: () => {
      toaster.error({ title: '献立にレシピが登録されていないか、食材データがありません' })
    },
  })

  const excludeMutation = useMutation({
    mutationFn: ({ itemId, isExcluded }: { itemId: string; isExcluded: boolean }) =>
      toggleExclude(itemId, isExcluded),
    onSuccess: (data) => {
      if (!result) return
      setResult({
        ...result,
        items: result.items.map((item) =>
          item.id === data.id ? { ...item, is_excluded: data.is_excluded } : item,
        ),
        summary: {
          ...result.summary,
          excluded_items: result.items.filter((i) =>
            i.id === data.id ? data.is_excluded : i.is_excluded,
          ).length,
          active_items: result.items.filter((i) =>
            i.id === data.id ? !data.is_excluded : !i.is_excluded,
          ).length,
        },
      })
    },
  })

  // Group items by category
  const groupedItems = useMemo(() => {
    if (!result) return []
    const groups = new Map<string, GeneratedItem[]>()
    for (const item of result.items) {
      const cat = item.category || 'その他'
      if (!groups.has(cat)) groups.set(cat, [])
      groups.get(cat)!.push(item)
    }
    return CATEGORY_ORDER
      .filter((cat) => groups.has(cat))
      .map((cat) => ({ category: cat, items: groups.get(cat)! }))
      .concat(
        [...groups.entries()]
          .filter(([cat]) => !CATEGORY_ORDER.includes(cat))
          .map(([cat, items]) => ({ category: cat, items }))
      )
  }, [result])

  if (!showForm && !result) {
    return (
      <Box mt={8} textAlign="center">
        <Button
          size="lg"
          minH="52px"
          bg="success.500"
          color="white"
          _hover={{ bg: 'success.600' }}
          onClick={() => setShowForm(true)}
          disabled={!hasRecipes}
          cursor="pointer"
          px={8}
          fontSize="md"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z" />
          </svg>
          この献立から買い物リストを作成
        </Button>
        {!hasRecipes && (
          <Text fontSize="md" color="text.muted" mt={2}>献立にレシピを追加してください</Text>
        )}
      </Box>
    )
  }

  if (showForm && !result) {
    return (
      <Box mt={8} bg="bg.card" p={6} borderRadius="xl" border="1px solid" borderColor="border.default">
        <Text fontSize="xl" fontWeight="bold" color="text.primary" mb={4}>買い物リストを生成</Text>
        <form onSubmit={(e) => { e.preventDefault(); generateMutation.mutate() }}>
          <VStack gap={4} align="stretch">
            <Box>
              <Text fontSize="md" fontWeight="bold" color="text.secondary" mb={1}>備考</Text>
              <Input
                placeholder="なるべく新鮮なものをお願いします"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                size="lg"
                fontSize="md"
                borderRadius="lg"
                minH="48px"
              />
            </Box>
            <HStack gap={3}>
              <Button
                type="submit"
                bg="success.500"
                color="white"
                _hover={{ bg: 'success.600' }}
                size="lg"
                minH="48px"
                loading={generateMutation.isPending}
                cursor="pointer"
                fontSize="md"
              >
                生成する
              </Button>
              <Button
                size="lg"
                minH="48px"
                variant="outline"
                onClick={() => setShowForm(false)}
                cursor="pointer"
                fontSize="md"
              >
                取消
              </Button>
            </HStack>
          </VStack>
        </form>
      </Box>
    )
  }

  if (!result) return null

  const excludedCount = result.items.filter((i) => i.is_excluded).length
  const activeCount = result.items.length - excludedCount

  return (
    <Box mt={8} bg="bg.card" p={6} borderRadius="xl" border="1px solid" borderColor="border.default">
      <HStack justify="space-between" mb={4}>
        <Text fontSize="xl" fontWeight="bold" color="text.primary">
          買い物リスト
        </Text>
        <Button
          size="md"
          minH="44px"
          variant="outline"
          onClick={() => { setResult(null); setShowForm(false) }}
          cursor="pointer"
          fontSize="md"
        >
          閉じる
        </Button>
      </HStack>

      {/* Summary */}
      <HStack mb={5} gap={3} flexWrap="wrap">
        <Badge bg="brand.50" color="brand.700" fontSize="md" px={4} py={2} borderRadius="lg">
          合計: {result.items.length}品
        </Badge>
        {excludedCount > 0 && (
          <Badge bg="warn.50" color="warn.600" fontSize="md" px={4} py={2} borderRadius="lg">
            除外: {excludedCount}品
          </Badge>
        )}
        <Badge bg="success.50" color="success.700" fontSize="md" px={4} py={2} borderRadius="lg">
          購入対象: {activeCount}品
        </Badge>
      </HStack>

      {/* Items grouped by category */}
      <VStack gap={5} align="stretch">
        {groupedItems.map(({ category, items }) => (
          <Box key={category}>
            <HStack mb={2} gap={2}>
              <Text fontSize="md" fontWeight="bold" color="text.secondary">{category}</Text>
              <Badge fontSize="xs" colorPalette="gray" variant="subtle">{items.length}</Badge>
            </HStack>
            <VStack gap={2} align="stretch">
              {items.map((item: GeneratedItem) => (
                <HStack
                  key={item.id}
                  justify="space-between"
                  bg={item.is_excluded ? 'gray.50' : 'bg.muted'}
                  p={4}
                  borderRadius="lg"
                  opacity={item.is_excluded ? 0.6 : 1}
                  transition="opacity 0.15s"
                >
                  <VStack align="start" gap={1} flex={1}>
                    <HStack gap={2} flexWrap="wrap">
                      <Text
                        fontSize="md"
                        fontWeight="medium"
                        color="text.primary"
                        textDecoration={item.is_excluded ? 'line-through' : 'none'}
                      >
                        {item.item_name}
                      </Text>
                      {item.quantity && (
                        <Text fontSize="md" color="text.muted">{item.quantity}</Text>
                      )}
                      {item.is_excluded && item.excluded_reason === 'pantry' && (
                        <Badge fontSize="sm" bg="warn.100" color="warn.600" px={2}>在庫あり</Badge>
                      )}
                    </HStack>
                    <Text fontSize="sm" color="text.muted">
                      {item.recipe_sources.join('、')}
                    </Text>
                  </VStack>
                  <Button
                    size="md"
                    minH="44px"
                    minW="80px"
                    variant={item.is_excluded ? 'outline' : 'ghost'}
                    colorPalette={item.is_excluded ? 'green' : 'orange'}
                    onClick={() => excludeMutation.mutate({ itemId: item.id, isExcluded: !item.is_excluded })}
                    cursor="pointer"
                    fontSize="md"
                  >
                    {item.is_excluded ? '復元' : '除外'}
                  </Button>
                </HStack>
              ))}
            </VStack>
          </Box>
        ))}
      </VStack>
    </Box>
  )
}
