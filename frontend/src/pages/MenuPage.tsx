import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Box, Button, Text, VStack, HStack, SimpleGrid, Badge, Input, Flex,
} from '@chakra-ui/react'
import { getWeeklyMenu, updateWeeklyMenu, copyWeeklyMenu, clearWeeklyMenu } from '@/api/menus'
import { getRecipes } from '@/api/recipes'
import type { MenuRecipeEntry, Recipe } from '@/types'
import PageHeader from '@/components/ui/PageHeader'
import LoadingState from '@/components/ui/LoadingState'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import { toaster } from '@/components/ui/toaster'
import ShoppingListGenerator from '@/components/menu/ShoppingListGenerator'

const DAYS = [
  { key: 'monday', label: '月曜日', short: '月' },
  { key: 'tuesday', label: '火曜日', short: '火' },
  { key: 'wednesday', label: '水曜日', short: '水' },
  { key: 'thursday', label: '木曜日', short: '木' },
  { key: 'friday', label: '金曜日', short: '金' },
  { key: 'saturday', label: '土曜日', short: '土' },
  { key: 'sunday', label: '日曜日', short: '日' },
]

const MEAL_LABELS: Record<string, string> = { breakfast: '朝食', dinner: '夕食' }
const MEAL_ICONS: Record<string, string> = { breakfast: '☀️', dinner: '🌙' }

const PICKER_CATEGORIES = [
  { value: '', label: 'すべて' },
  { value: '和食', label: '🍱 和食' },
  { value: '洋食', label: '🍝 洋食' },
  { value: '中華', label: '🥡 中華' },
  { value: 'その他', label: '🍽️ その他' },
]
const PICKER_TYPES = [
  { value: '', label: 'すべて' },
  { value: '主菜', label: '主菜' },
  { value: '副菜', label: '副菜' },
  { value: '汁物', label: '汁物' },
  { value: 'ご飯', label: 'ご飯' },
  { value: 'その他', label: 'その他' },
]
const PICKER_DIFFICULTIES = [
  { value: '', label: 'すべて' },
  { value: '簡単', label: '簡単' },
  { value: '普通', label: '普通' },
  { value: '難しい', label: '難しい' },
]

function getWeekStartDate(offset: number): string {
  const now = new Date()
  const day = now.getDay()
  const monday = new Date(now)
  monday.setDate(now.getDate() - ((day + 6) % 7) + offset * 7)
  return monday.toISOString().split('T')[0]
}

function formatWeekDisplay(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00')
  const month = date.getMonth() + 1
  const day = date.getDate()
  const endDate = new Date(date)
  endDate.setDate(date.getDate() + 6)
  const endMonth = endDate.getMonth() + 1
  const endDay = endDate.getDate()
  if (month === endMonth) {
    return `${month}月${day}日〜${endDay}日`
  }
  return `${month}月${day}日〜${endMonth}月${endDay}日`
}

function isCurrentWeek(dateStr: string): boolean {
  const current = getWeekStartDate(0)
  return dateStr === current
}

export default function MenuPage() {
  const [weekOffset, setWeekOffset] = useState(0)
  const weekStart = useMemo(() => getWeekStartDate(weekOffset), [weekOffset])
  const queryClient = useQueryClient()
  const [showClearConfirm, setShowClearConfirm] = useState(false)

  // Recipe picker state
  const [pickerSlot, setPickerSlot] = useState<{ day: string; meal: string } | null>(null)
  const [pickerSearch, setPickerSearch] = useState('')
  const [pickerCategory, setPickerCategory] = useState('')
  const [pickerType, setPickerType] = useState('')
  const [pickerDifficulty, setPickerDifficulty] = useState('')

  const { data: menuData, isLoading } = useQuery({
    queryKey: ['menu', weekStart],
    queryFn: () => getWeeklyMenu(weekStart),
  })

  const { data: recipesData } = useQuery({
    queryKey: ['recipes', 'all'],
    queryFn: () => getRecipes({ limit: 100 }),
  })

  const filteredRecipes = useMemo(() => {
    if (!recipesData?.recipes) return []
    let results = recipesData.recipes
    if (pickerCategory) {
      results = results.filter((r: Recipe) => r.category === pickerCategory)
    }
    if (pickerType) {
      results = results.filter((r: Recipe) => r.type === pickerType)
    }
    if (pickerDifficulty) {
      results = results.filter((r: Recipe) => r.difficulty === pickerDifficulty)
    }
    if (pickerSearch) {
      const q = pickerSearch.toLowerCase()
      results = results.filter((r: Recipe) =>
        r.name.toLowerCase().includes(q) ||
        r.category.includes(q) ||
        r.type.includes(q)
      )
    }
    return results
  }, [recipesData, pickerSearch, pickerCategory, pickerType, pickerDifficulty])

  const updateMutation = useMutation({
    mutationFn: (params: { menus: Record<string, { breakfast: { recipe_id: string; recipe_type: string }[]; dinner: { recipe_id: string; recipe_type: string }[] }> }) =>
      updateWeeklyMenu(weekStart, params.menus),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['menu', weekStart] })
      toaster.success({ title: '献立を更新しました' })
    },
  })

  const copyMutation = useMutation({
    mutationFn: () => copyWeeklyMenu(getWeekStartDate(weekOffset - 1), weekStart),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['menu', weekStart] })
      toaster.success({ title: '前週の献立をコピーしました' })
    },
  })

  const clearMutation = useMutation({
    mutationFn: () => clearWeeklyMenu(weekStart),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['menu', weekStart] })
      setShowClearConfirm(false)
      toaster.success({ title: '献立をクリアしました' })
    },
  })

  const buildMenuPayload = () => {
    if (!menuData) return {}
    const updateMenus: Record<string, { breakfast: { recipe_id: string; recipe_type: string }[]; dinner: { recipe_id: string; recipe_type: string }[] }> = {}
    for (const d of DAYS) {
      const slot = menuData.menus[d.key] || { breakfast: [], dinner: [] }
      updateMenus[d.key] = {
        breakfast: slot.breakfast.map((e: MenuRecipeEntry) => ({ recipe_id: e.recipe.id, recipe_type: e.recipe_type })),
        dinner: slot.dinner.map((e: MenuRecipeEntry) => ({ recipe_id: e.recipe.id, recipe_type: e.recipe_type })),
      }
    }
    return updateMenus
  }

  const handlePickRecipe = (recipe: Recipe) => {
    if (!pickerSlot || !menuData) return

    const updateMenus = buildMenuPayload()
    const { day, meal } = pickerSlot

    if (!updateMenus[day]) {
      updateMenus[day] = { breakfast: [], dinner: [] }
    }

    updateMenus[day][meal as 'breakfast' | 'dinner'].push({
      recipe_id: recipe.id,
      recipe_type: recipe.type,
    })

    updateMutation.mutate({ menus: updateMenus })
    setPickerSlot(null)
    setPickerSearch('')
    setPickerCategory('')
    setPickerType('')
    setPickerDifficulty('')
  }

  const handleRemoveRecipe = (day: string, meal: string, index: number) => {
    if (!menuData) return
    const updateMenus = buildMenuPayload()
    updateMenus[day][meal as 'breakfast' | 'dinner'].splice(index, 1)
    updateMutation.mutate({ menus: updateMenus })
  }

  return (
    <Box>
      <PageHeader title="週間献立">
        <HStack gap={3}>
          <Button
            size="lg"
            minH="48px"
            variant="outline"
            onClick={() => copyMutation.mutate()}
            loading={copyMutation.isPending}
            cursor="pointer"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
            </svg>
            前週コピー
          </Button>
        </HStack>
      </PageHeader>

      {/* Week Navigation */}
      <Box bg="bg.card" borderRadius="xl" border="1px solid" borderColor="border.default" p={5} mb={6}>
        <HStack justify="space-between" align="center">
          <Button
            variant="outline"
            size="lg"
            minH="48px"
            minW="48px"
            onClick={() => setWeekOffset((w) => w - 1)}
            cursor="pointer"
            aria-label="前の週"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </Button>
          <VStack gap={1}>
            <Text fontSize="xl" fontWeight="bold" color="text.primary">
              {formatWeekDisplay(weekStart)}
            </Text>
            {isCurrentWeek(weekStart) && (
              <Badge bg="brand.100" color="brand.700" fontSize="sm" px={3} py={0.5} borderRadius="full">
                今週
              </Badge>
            )}
            {weekOffset !== 0 && (
              <Button
                size="sm"
                variant="ghost"
                color="brand.600"
                onClick={() => setWeekOffset(0)}
                cursor="pointer"
                fontSize="sm"
              >
                今週に戻る
              </Button>
            )}
          </VStack>
          <Button
            variant="outline"
            size="lg"
            minH="48px"
            minW="48px"
            onClick={() => setWeekOffset((w) => w + 1)}
            cursor="pointer"
            aria-label="次の週"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </Button>
        </HStack>
      </Box>

      {/* Summary */}
      {menuData?.summary && menuData.summary.total_recipes > 0 && (
        <HStack mb={6} gap={4} justify="center" flexWrap="wrap">
          <Badge bg="brand.50" color="brand.700" fontSize="md" px={4} py={2} borderRadius="lg">
            レシピ数: {menuData.summary.total_recipes}
          </Badge>
          <Badge bg="success.50" color="success.700" fontSize="md" px={4} py={2} borderRadius="lg">
            平均調理時間: {menuData.summary.avg_cooking_time}分
          </Badge>
        </HStack>
      )}

      {isLoading ? (
        <LoadingState type="cards" count={7} />
      ) : (
        <>
          {/* Desktop: Grid, Mobile: Stack */}
          <SimpleGrid columns={{ base: 1, md: 2, lg: 3, xl: 4 }} gap={5}>
            {DAYS.map(({ key, label }) => {
              const dayMenu = menuData?.menus[key]
              return (
                <Box
                  key={key}
                  bg="bg.card"
                  borderRadius="xl"
                  border="1px solid"
                  borderColor="border.default"
                  overflow="hidden"
                >
                  {/* Day Header */}
                  <Box
                    bg={key === 'saturday' ? 'blue.50' : key === 'sunday' ? 'red.50' : 'brand.50'}
                    px={4}
                    py={3}
                    borderBottom="1px solid"
                    borderColor="border.default"
                  >
                    <Text
                      fontSize="lg"
                      fontWeight="bold"
                      color={key === 'saturday' ? 'blue.700' : key === 'sunday' ? 'red.600' : 'brand.700'}
                      textAlign="center"
                    >
                      {label}
                    </Text>
                  </Box>

                  <Box p={4}>
                    {(['breakfast', 'dinner'] as const).map((meal) => {
                      const entries = dayMenu?.[meal] || []
                      return (
                        <Box key={meal} mb={5} _last={{ mb: 0 }}>
                          <HStack mb={2} gap={1}>
                            <Text fontSize="md">{MEAL_ICONS[meal]}</Text>
                            <Text fontSize="md" fontWeight="bold" color="text.secondary">
                              {MEAL_LABELS[meal]}
                            </Text>
                          </HStack>
                          <VStack align="stretch" gap={2}>
                            {entries.map((entry: MenuRecipeEntry, idx: number) => (
                              <HStack
                                key={idx}
                                justify="space-between"
                                bg="bg.muted"
                                p={3}
                                borderRadius="lg"
                                _hover={{ bg: 'gray.100' }}
                                transition="background 0.15s"
                              >
                                <VStack align="start" gap={0} flex={1}>
                                  <Text fontSize="md" fontWeight="medium" color="text.primary">{entry.recipe.name}</Text>
                                  <Text fontSize="sm" color="text.muted">{entry.recipe_type} · {entry.recipe.cooking_time}分</Text>
                                </VStack>
                                <Button
                                  size="md"
                                  minH="40px"
                                  minW="40px"
                                  colorPalette="red"
                                  variant="ghost"
                                  onClick={() => handleRemoveRecipe(key, meal, idx)}
                                  cursor="pointer"
                                  aria-label="レシピを削除"
                                >
                                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                                  </svg>
                                </Button>
                              </HStack>
                            ))}
                            {entries.length === 0 && (
                              <Text fontSize="sm" color="text.muted" fontStyle="italic" py={1}>未設定</Text>
                            )}
                          </VStack>

                          <Button
                            size="md"
                            minH="44px"
                            variant="outline"
                            mt={2}
                            w="100%"
                            color="brand.600"
                            borderColor="brand.200"
                            _hover={{ bg: 'brand.50', borderColor: 'brand.400' }}
                            onClick={() => { setPickerSlot({ day: key, meal }); setPickerSearch('') }}
                            cursor="pointer"
                            fontSize="md"
                          >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
                            </svg>
                            レシピを追加
                          </Button>
                        </Box>
                      )
                    })}
                  </Box>
                </Box>
              )
            })}
          </SimpleGrid>

          {/* Clear button at bottom, subdued */}
          <HStack justify="center" mt={6}>
            <Button
              size="md"
              minH="44px"
              variant="ghost"
              color="text.muted"
              _hover={{ color: 'red.500' }}
              onClick={() => setShowClearConfirm(true)}
              cursor="pointer"
              fontSize="sm"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
              この週の献立をすべてクリア
            </Button>
          </HStack>
        </>
      )}

      {/* Recipe Picker Overlay */}
      {pickerSlot && (
        <Box
          position="fixed"
          top={0}
          left={0}
          right={0}
          bottom={0}
          bg="blackAlpha.500"
          zIndex={50}
          display="flex"
          alignItems="center"
          justifyContent="center"
          p={4}
          onClick={(e) => { if (e.target === e.currentTarget) { setPickerSlot(null); setPickerSearch(''); setPickerCategory(''); setPickerType(''); setPickerDifficulty('') } }}
        >
          <Box
            bg="bg.card"
            p={6}
            borderRadius="2xl"
            border="1px solid"
            borderColor="border.default"
            shadow="xl"
            w="100%"
            maxW="900px"
            maxH="80vh"
            display="flex"
            flexDirection="column"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Picker Header */}
            <HStack justify="space-between" mb={4}>
              <VStack align="start" gap={0}>
                <Text fontSize="lg" fontWeight="bold" color="text.primary">
                  レシピを選択
                </Text>
                <Text fontSize="sm" color="text.muted">
                  {DAYS.find((d) => d.key === pickerSlot.day)?.label} {MEAL_LABELS[pickerSlot.meal]}
                </Text>
              </VStack>
              <Button
                size="md"
                minH="44px"
                minW="44px"
                variant="ghost"
                onClick={() => { setPickerSlot(null); setPickerSearch(''); setPickerCategory(''); setPickerType(''); setPickerDifficulty('') }}
                cursor="pointer"
                aria-label="閉じる"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </Button>
            </HStack>

            {/* Search */}
            <Input
              placeholder="レシピ名で検索..."
              value={pickerSearch}
              onChange={(e) => setPickerSearch(e.target.value)}
              size="lg"
              fontSize="md"
              borderRadius="lg"
              minH="48px"
              mb={3}
              autoFocus
            />

            {/* Filters */}
            <SimpleGrid columns={{ base: 1, sm: 3 }} gap={2} mb={3}>
              <Box>
                <Text fontSize="xs" fontWeight="bold" color="text.secondary" mb={1}>カテゴリ</Text>
                <Flex gap={1} flexWrap="wrap">
                  {PICKER_CATEGORIES.map((cat) => (
                    <Button
                      key={cat.value}
                      size="sm"
                      minH="36px"
                      px={3}
                      variant={pickerCategory === cat.value ? 'solid' : 'outline'}
                      bg={pickerCategory === cat.value ? 'brand.600' : undefined}
                      color={pickerCategory === cat.value ? 'white' : 'text.primary'}
                      borderRadius="full"
                      onClick={() => setPickerCategory(cat.value)}
                      cursor="pointer"
                      fontSize="sm"
                    >
                      {cat.label}
                    </Button>
                  ))}
                </Flex>
              </Box>
              <Box>
                <Text fontSize="xs" fontWeight="bold" color="text.secondary" mb={1}>種類</Text>
                <Flex gap={1} flexWrap="wrap">
                  {PICKER_TYPES.map((t) => (
                    <Button
                      key={t.value}
                      size="sm"
                      minH="36px"
                      px={3}
                      variant={pickerType === t.value ? 'solid' : 'outline'}
                      bg={pickerType === t.value ? 'cyan.600' : undefined}
                      color={pickerType === t.value ? 'white' : 'text.primary'}
                      borderRadius="full"
                      onClick={() => setPickerType(t.value)}
                      cursor="pointer"
                      fontSize="sm"
                    >
                      {t.label}
                    </Button>
                  ))}
                </Flex>
              </Box>
              <Box>
                <Text fontSize="xs" fontWeight="bold" color="text.secondary" mb={1}>難易度</Text>
                <Flex gap={1} flexWrap="wrap">
                  {PICKER_DIFFICULTIES.map((d) => (
                    <Button
                      key={d.value}
                      size="sm"
                      minH="36px"
                      px={3}
                      variant={pickerDifficulty === d.value ? 'solid' : 'outline'}
                      bg={pickerDifficulty === d.value
                        ? d.value === '簡単' ? 'green.500' : d.value === '普通' ? 'orange.500' : d.value === '難しい' ? 'red.500' : 'brand.600'
                        : undefined}
                      color={pickerDifficulty === d.value ? 'white' : 'text.primary'}
                      borderRadius="full"
                      onClick={() => setPickerDifficulty(d.value)}
                      cursor="pointer"
                      fontSize="sm"
                    >
                      {d.label}
                    </Button>
                  ))}
                </Flex>
              </Box>
            </SimpleGrid>

            {/* Recipe Grid */}
            <Box flex={1} overflowY="auto">
              {filteredRecipes.length === 0 ? (
                <Text fontSize="md" color="text.muted" textAlign="center" py={8}>
                  レシピが見つかりません
                </Text>
              ) : (
                <SimpleGrid columns={{ base: 2, sm: 3 }} gap={2}>
                  {filteredRecipes.map((recipe: Recipe) => (
                    <Box
                      key={recipe.id}
                      p={3}
                      bg="bg.muted"
                      borderRadius="lg"
                      _hover={{ bg: 'brand.50', borderColor: 'brand.300' }}
                      border="1px solid"
                      borderColor="transparent"
                      transition="all 0.15s"
                      cursor="pointer"
                      onClick={() => handlePickRecipe(recipe)}
                    >
                      <Text fontSize="md" fontWeight="medium" color="text.primary" lineClamp={1}>
                        {recipe.name}
                      </Text>
                      <HStack gap={1} mt={1} flexWrap="wrap">
                        <Badge colorPalette="blue" variant="subtle" fontSize="xs">{recipe.category}</Badge>
                        <Badge colorPalette="cyan" variant="subtle" fontSize="xs">{recipe.type}</Badge>
                        <Text fontSize="xs" color="text.muted">{recipe.cooking_time}分</Text>
                      </HStack>
                    </Box>
                  ))}
                </SimpleGrid>
              )}
            </Box>
          </Box>
        </Box>
      )}

      {/* Shopping List Generator */}
      <ShoppingListGenerator
        weekStart={weekStart}
        hasRecipes={(menuData?.summary.total_recipes ?? 0) > 0}
      />

      <ConfirmDialog
        open={showClearConfirm}
        onClose={() => setShowClearConfirm(false)}
        onConfirm={() => clearMutation.mutate()}
        title="献立をクリア"
        message="この週の献立をすべてクリアしますか？この操作は取り消せません。"
        loading={clearMutation.isPending}
      />
    </Box>
  )
}
