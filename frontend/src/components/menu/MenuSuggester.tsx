import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  Box, Button, Text, VStack, HStack, SimpleGrid, Badge, Input, Textarea, Flex,
} from '@chakra-ui/react'
import { suggestMenu, updateWeeklyMenu } from '@/api/menus'
import type {
  WeeklyMenuSuggestionResponse,
  SuggestedRecipeRef,
  MealSlotUpdate,
} from '@/types'
import { toaster } from '@/components/ui/toaster'

interface Props {
  weekStart: string
  onApplied: () => void
}

const DAYS = [
  { key: 'monday', label: '月曜日' },
  { key: 'tuesday', label: '火曜日' },
  { key: 'wednesday', label: '水曜日' },
  { key: 'thursday', label: '木曜日' },
  { key: 'friday', label: '金曜日' },
  { key: 'saturday', label: '土曜日' },
  { key: 'sunday', label: '日曜日' },
]

const MEAL_LABELS: Record<string, string> = { breakfast: '朝食', dinner: '夕食' }
const MEAL_ICONS: Record<string, string> = { breakfast: '☀️', dinner: '🌙' }

const DIET_PRESETS = [
  { value: '柔らかい食事', label: '柔らかい食事' },
  { value: '塩分控えめ', label: '塩分控えめ' },
  { value: '脂質控えめ', label: '脂質控えめ' },
  { value: '糖質控えめ', label: '糖質控えめ' },
]

function formatErrorMessage(err: unknown): string {
  const e = err as { response?: { status?: number; data?: { detail?: string } } }
  const detail = e?.response?.data?.detail
  if (detail) return detail
  const status = e?.response?.status
  if (status === 503) return '献立提案サービスに接続できません'
  if (status === 504) return '提案に時間がかかりすぎました。もう一度お試しください'
  if (status === 502) return '提案の解析に失敗しました。もう一度お試しください'
  if (status === 400) return 'レシピが登録されていません'
  return '献立の提案に失敗しました'
}

export default function MenuSuggester({ weekStart, onApplied }: Props) {
  const [showForm, setShowForm] = useState(false)
  const [result, setResult] = useState<WeeklyMenuSuggestionResponse | null>(null)
  const [dietarySet, setDietarySet] = useState<Set<string>>(new Set())
  const [avoidInput, setAvoidInput] = useState('')
  const [notes, setNotes] = useState('')

  const suggestMutation = useMutation({
    mutationFn: () =>
      suggestMenu({
        week_start: weekStart,
        dietary_restrictions: Array.from(dietarySet),
        avoid_ingredients: avoidInput
          .split(/[,、]/)
          .map((s) => s.trim())
          .filter(Boolean),
        notes: notes || undefined,
      }),
    onSuccess: (data) => {
      setResult(data)
      setShowForm(false)
    },
    onError: (err) => {
      toaster.error({ title: formatErrorMessage(err) })
    },
  })

  const applyMutation = useMutation({
    mutationFn: () => {
      if (!result) throw new Error('no result')
      const menus: Record<string, MealSlotUpdate> = {}
      for (const day of DAYS) {
        const slot = result.menus[day.key] || { breakfast: [], dinner: [] }
        menus[day.key] = {
          breakfast: slot.breakfast.map((r: SuggestedRecipeRef) => ({
            recipe_id: r.recipe_id,
            recipe_type: r.recipe_type,
          })),
          dinner: slot.dinner.map((r: SuggestedRecipeRef) => ({
            recipe_id: r.recipe_id,
            recipe_type: r.recipe_type,
          })),
        }
      }
      return updateWeeklyMenu(weekStart, menus)
    },
    onSuccess: () => {
      toaster.success({ title: '献立を適用しました' })
      setResult(null)
      onApplied()
    },
    onError: () => {
      toaster.error({ title: '献立の適用に失敗しました' })
    },
  })

  const toggleDietary = (value: string) => {
    setDietarySet((prev) => {
      const next = new Set(prev)
      if (next.has(value)) next.delete(value)
      else next.add(value)
      return next
    })
  }

  // --- 初期状態: 「AI提案」ボタンのみ ---
  if (!showForm && !result && !suggestMutation.isPending) {
    return (
      <Box mb={6} textAlign="center">
        <Button
          size="lg"
          minH="52px"
          bg="brand.600"
          color="white"
          _hover={{ bg: 'brand.700' }}
          onClick={() => setShowForm(true)}
          cursor="pointer"
          px={8}
          fontSize="md"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2l1.8 5.6h5.9l-4.8 3.5 1.8 5.6-4.7-3.5-4.7 3.5 1.8-5.6L4.3 7.6h5.9L12 2z" />
          </svg>
          AIが今週の献立を提案します
        </Button>
        <Text fontSize="sm" color="text.muted" mt={2}>
          好みを選ぶだけで、1週間分の献立を自動で組み立てます
        </Text>
      </Box>
    )
  }

  // --- 入力フォーム ---
  if (showForm && !suggestMutation.isPending) {
    return (
      <Box mb={6} bg="bg.card" p={6} borderRadius="xl" border="1px solid" borderColor="border.default">
        <Text fontSize="xl" fontWeight="bold" color="text.primary" mb={4}>
          AI献立提案
        </Text>
        <form onSubmit={(e) => { e.preventDefault(); suggestMutation.mutate() }}>
          <VStack gap={5} align="stretch">
            <Box>
              <Text fontSize="md" fontWeight="bold" color="text.secondary" mb={2}>
                食事制限・配慮（複数選択可）
              </Text>
              <Flex gap={2} flexWrap="wrap">
                {DIET_PRESETS.map((d) => {
                  const active = dietarySet.has(d.value)
                  return (
                    <Button
                      key={d.value}
                      type="button"
                      size="md"
                      minH="44px"
                      px={4}
                      variant={active ? 'solid' : 'outline'}
                      bg={active ? 'brand.600' : undefined}
                      color={active ? 'white' : 'text.primary'}
                      borderRadius="full"
                      onClick={() => toggleDietary(d.value)}
                      cursor="pointer"
                      fontSize="md"
                    >
                      {d.label}
                    </Button>
                  )
                })}
              </Flex>
            </Box>

            <Box>
              <Text fontSize="md" fontWeight="bold" color="text.secondary" mb={1}>
                避けたい食材（カンマ区切り）
              </Text>
              <Input
                placeholder="例: えび、生卵"
                value={avoidInput}
                onChange={(e) => setAvoidInput(e.target.value)}
                size="lg"
                fontSize="md"
                borderRadius="lg"
                minH="48px"
              />
            </Box>

            <Box>
              <Text fontSize="md" fontWeight="bold" color="text.secondary" mb={1}>
                その他ご要望
              </Text>
              <Textarea
                placeholder="例: 汁物は味噌汁中心にしてください"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                size="lg"
                fontSize="md"
                borderRadius="lg"
                minH="80px"
              />
            </Box>

            <HStack gap={3}>
              <Button
                type="submit"
                bg="brand.600"
                color="white"
                _hover={{ bg: 'brand.700' }}
                size="lg"
                minH="48px"
                cursor="pointer"
                fontSize="md"
              >
                提案してもらう
              </Button>
              <Button
                type="button"
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

  // --- ローディング ---
  if (suggestMutation.isPending) {
    return (
      <Box mb={6} bg="bg.card" p={8} borderRadius="xl" border="1px solid" borderColor="border.default" textAlign="center">
        <VStack gap={3}>
          <Box
            as="span"
            display="inline-block"
            w="48px"
            h="48px"
            borderRadius="full"
            border="4px solid"
            borderColor="brand.200"
            borderTopColor="brand.600"
            animation="spin 0.9s linear infinite"
            css={{ '@keyframes spin': { to: { transform: 'rotate(360deg)' } } }}
          />
          <Text fontSize="lg" fontWeight="bold" color="text.primary">
            AIが考えています…
          </Text>
          <Text fontSize="md" color="text.muted">
            最大3〜4分ほどかかります
          </Text>
        </VStack>
      </Box>
    )
  }

  // --- 提案プレビュー ---
  if (result) {
    const totalSlots = DAYS.reduce((acc, d) => {
      const slot = result.menus[d.key]
      return acc + (slot?.breakfast?.length || 0) + (slot?.dinner?.length || 0)
    }, 0)

    return (
      <Box mb={6} bg="bg.card" p={6} borderRadius="xl" border="1px solid" borderColor="brand.300">
        <HStack justify="space-between" mb={4} flexWrap="wrap" gap={3}>
          <VStack align="start" gap={0}>
            <Text fontSize="xl" fontWeight="bold" color="text.primary">
              AI提案プレビュー
            </Text>
            <Text fontSize="sm" color="text.muted">
              合計 {totalSlots} 品 ・ 適用するまで献立は変更されません
            </Text>
          </VStack>
          <HStack gap={2}>
            <Button
              size="lg"
              minH="48px"
              variant="outline"
              onClick={() => { setResult(null); setShowForm(true) }}
              cursor="pointer"
              fontSize="md"
            >
              やり直す
            </Button>
            <Button
              size="lg"
              minH="48px"
              bg="success.500"
              color="white"
              _hover={{ bg: 'success.600' }}
              onClick={() => applyMutation.mutate()}
              loading={applyMutation.isPending}
              cursor="pointer"
              fontSize="md"
            >
              この提案を適用
            </Button>
          </HStack>
        </HStack>

        {result.rationale && (
          <Box bg="brand.50" p={3} borderRadius="lg" mb={4}>
            <Text fontSize="sm" color="brand.700">
              {result.rationale}
            </Text>
          </Box>
        )}

        <SimpleGrid columns={{ base: 1, md: 2, lg: 3, xl: 4 }} gap={4}>
          {DAYS.map(({ key, label }) => {
            const slot = result.menus[key] || { breakfast: [], dinner: [] }
            return (
              <Box
                key={key}
                bg="bg.muted"
                borderRadius="lg"
                border="1px solid"
                borderColor="border.default"
                p={3}
              >
                <Text fontSize="md" fontWeight="bold" color="text.primary" mb={2}>
                  {label}
                </Text>
                {(['breakfast', 'dinner'] as const).map((meal) => (
                  <Box key={meal} mb={2} _last={{ mb: 0 }}>
                    <HStack gap={1} mb={1}>
                      <Text fontSize="sm">{MEAL_ICONS[meal]}</Text>
                      <Text fontSize="sm" fontWeight="bold" color="text.secondary">
                        {MEAL_LABELS[meal]}
                      </Text>
                    </HStack>
                    <VStack align="stretch" gap={1}>
                      {slot[meal].length === 0 ? (
                        <Text fontSize="sm" color="text.muted" fontStyle="italic">—</Text>
                      ) : (
                        slot[meal].map((r, idx) => (
                          <HStack key={idx} gap={2} flexWrap="wrap">
                            <Badge colorPalette="cyan" variant="subtle" fontSize="xs">
                              {r.recipe_type}
                            </Badge>
                            <Text fontSize="sm" color="text.primary" lineClamp={1}>
                              {r.name}
                            </Text>
                          </HStack>
                        ))
                      )}
                    </VStack>
                  </Box>
                ))}
              </Box>
            )
          })}
        </SimpleGrid>
      </Box>
    )
  }

  return null
}
