import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Box, Button, Input, SimpleGrid, Text, VStack, HStack, Badge, Textarea, Flex,
} from '@chakra-ui/react'
import { getRecipes, createRecipe, updateRecipe, deleteRecipe } from '@/api/recipes'
import type { Recipe } from '@/types'
import PageHeader from '@/components/ui/PageHeader'
import FormField from '@/components/ui/FormField'
import LoadingState from '@/components/ui/LoadingState'
import EmptyState from '@/components/ui/EmptyState'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import { toaster } from '@/components/ui/toaster'
import IngredientsEditor from '@/components/recipes/IngredientsEditor'

const categories = [
  { value: '', label: 'すべて' },
  { value: '和食', label: '和食' },
  { value: '洋食', label: '洋食' },
  { value: '中華', label: '中華' },
  { value: 'その他', label: 'その他' },
]
const types = [
  { value: '', label: 'すべて' },
  { value: '主菜', label: '主菜' },
  { value: '副菜', label: '副菜' },
  { value: '汁物', label: '汁物' },
  { value: 'ご飯', label: 'ご飯' },
  { value: 'その他', label: 'その他' },
]
const difficulties = [
  { value: '', label: 'すべて' },
  { value: '簡単', label: '簡単' },
  { value: '普通', label: '普通' },
  { value: '難しい', label: '難しい' },
]

const formCategories = categories.filter((c) => c.value !== '')
const formTypes = types.filter((t) => t.value !== '')
const formDifficulties = difficulties.filter((d) => d.value !== '')

const emptyForm = {
  name: '',
  category: '和食',
  type: '主菜',
  difficulty: '簡単',
  cooking_time: 30,
  ingredients: '',
  instructions: '',
  memo: '',
  recipe_url: '',
}

const difficultyColor: Record<string, string> = {
  '簡単': 'green',
  '普通': 'orange',
  '難しい': 'red',
}

const categoryIcon: Record<string, string> = {
  '和食': '🍱',
  '洋食': '🍝',
  '中華': '🥡',
  'その他': '🍽️',
}

export default function RecipesPage() {
  const [search, setSearch] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const [filterType, setFilterType] = useState('')
  const [filterDifficulty, setFilterDifficulty] = useState('')
  const [page, setPage] = useState(1)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [detailRecipe, setDetailRecipe] = useState<Recipe | null>(null)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['recipes', { search, page, category: filterCategory, type: filterType, difficulty: filterDifficulty }],
    queryFn: () => getRecipes({
      search: search || undefined,
      category: filterCategory || undefined,
      type: filterType || undefined,
      difficulty: filterDifficulty || undefined,
      page,
      limit: 12,
    }),
  })

  const createMutation = useMutation({
    mutationFn: () => createRecipe({
      ...form,
      cooking_time: Number(form.cooking_time),
      ingredients: form.ingredients || undefined,
      instructions: form.instructions || undefined,
      memo: form.memo || undefined,
      recipe_url: form.recipe_url || undefined,
    } as Omit<Recipe, 'id' | 'created_at' | 'updated_at'>),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] })
      resetForm()
      toaster.success({ title: 'レシピを追加しました' })
    },
  })

  const updateMutation = useMutation({
    mutationFn: () => updateRecipe(editingId!, {
      ...form,
      cooking_time: Number(form.cooking_time),
      ingredients: form.ingredients || undefined,
      instructions: form.instructions || undefined,
      memo: form.memo || undefined,
      recipe_url: form.recipe_url || undefined,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] })
      resetForm()
      toaster.success({ title: 'レシピを更新しました' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteRecipe(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] })
      setDeleteTarget(null)
      setDetailRecipe(null)
      toaster.success({ title: 'レシピを削除しました' })
    },
  })

  const resetForm = () => {
    setForm(emptyForm)
    setShowForm(false)
    setEditingId(null)
  }

  const startEdit = useCallback((recipe: Recipe) => {
    setForm({
      name: recipe.name,
      category: recipe.category,
      type: recipe.type,
      difficulty: recipe.difficulty,
      cooking_time: recipe.cooking_time,
      ingredients: recipe.ingredients || '',
      instructions: recipe.instructions || '',
      memo: recipe.memo || '',
      recipe_url: recipe.recipe_url || '',
    })
    setEditingId(recipe.id)
    setDetailRecipe(null)
    setShowForm(true)
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingId) {
      updateMutation.mutate()
    } else {
      createMutation.mutate()
    }
  }

  const resetFilters = () => {
    setFilterCategory('')
    setFilterType('')
    setFilterDifficulty('')
    setSearch('')
    setPage(1)
  }

  const hasActiveFilters = filterCategory || filterType || filterDifficulty || search
  const isSaving = createMutation.isPending || updateMutation.isPending

  return (
    <Box>
      <PageHeader title="レシピ一覧">
        <Button
          bg="brand.600"
          color="white"
          _hover={{ bg: 'brand.700' }}
          size="lg"
          minH="48px"
          px={6}
          onClick={() => { resetForm(); setShowForm(true) }}
          cursor="pointer"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          新規追加
        </Button>
      </PageHeader>

      {/* Form Modal Overlay */}
      {showForm && (
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
          onClick={(e) => { if (e.target === e.currentTarget) resetForm() }}
        >
          <Box
            bg="bg.card"
            p={8}
            borderRadius="2xl"
            border="1px solid"
            borderColor="border.default"
            shadow="xl"
            w="100%"
            maxW="640px"
            maxH="90vh"
            overflowY="auto"
            onClick={(e) => e.stopPropagation()}
          >
            <Text fontSize="xl" fontWeight="bold" color="text.primary" mb={6}>
              {editingId ? 'レシピを編集' : '新しいレシピを追加'}
            </Text>
            <form onSubmit={handleSubmit}>
              <VStack gap={5} align="stretch">
                <FormField label="レシピ名" required>
                  <Input
                    placeholder="レシピ名を入力"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    size="lg"
                    fontSize="md"
                    borderRadius="lg"
                    minH="48px"
                    required
                  />
                </FormField>
                <VStack gap={4} align="stretch">
                  <FormField label="カテゴリ">
                    <Flex gap={2} flexWrap="wrap">
                      {formCategories.map((cat) => (
                        <Button
                          key={cat.value}
                          type="button"
                          size="md"
                          minH="44px"
                          px={5}
                          variant={form.category === cat.value ? 'solid' : 'outline'}
                          bg={form.category === cat.value ? 'brand.600' : undefined}
                          color={form.category === cat.value ? 'white' : 'text.primary'}
                          _hover={{ bg: form.category === cat.value ? 'brand.700' : 'brand.50' }}
                          borderRadius="full"
                          onClick={() => setForm({ ...form, category: cat.value })}
                          cursor="pointer"
                          fontSize="md"
                        >
                          {categoryIcon[cat.value] ? `${categoryIcon[cat.value]} ` : ''}{cat.label}
                        </Button>
                      ))}
                    </Flex>
                  </FormField>
                  <FormField label="種類">
                    <Flex gap={2} flexWrap="wrap">
                      {formTypes.map((t) => (
                        <Button
                          key={t.value}
                          type="button"
                          size="md"
                          minH="44px"
                          px={5}
                          variant={form.type === t.value ? 'solid' : 'outline'}
                          bg={form.type === t.value ? 'cyan.600' : undefined}
                          color={form.type === t.value ? 'white' : 'text.primary'}
                          _hover={{ bg: form.type === t.value ? 'cyan.700' : 'cyan.50' }}
                          borderRadius="full"
                          onClick={() => setForm({ ...form, type: t.value })}
                          cursor="pointer"
                          fontSize="md"
                        >
                          {t.label}
                        </Button>
                      ))}
                    </Flex>
                  </FormField>
                  <FormField label="難易度">
                    <Flex gap={2} flexWrap="wrap">
                      {formDifficulties.map((d) => (
                        <Button
                          key={d.value}
                          type="button"
                          size="md"
                          minH="44px"
                          px={5}
                          variant={form.difficulty === d.value ? 'solid' : 'outline'}
                          bg={form.difficulty === d.value ? `${difficultyColor[d.value]}.600` : undefined}
                          color={form.difficulty === d.value ? 'white' : 'text.primary'}
                          _hover={{ bg: form.difficulty === d.value ? `${difficultyColor[d.value]}.700` : 'gray.50' }}
                          borderRadius="full"
                          onClick={() => setForm({ ...form, difficulty: d.value })}
                          cursor="pointer"
                          fontSize="md"
                        >
                          {d.label}
                        </Button>
                      ))}
                    </Flex>
                  </FormField>
                </VStack>
                <FormField label="調理時間（分）" required>
                  <Input
                    type="number"
                    value={form.cooking_time}
                    onChange={(e) => setForm({ ...form, cooking_time: Number(e.target.value) })}
                    size="lg"
                    fontSize="md"
                    borderRadius="lg"
                    minH="48px"
                    min={1}
                    required
                  />
                </FormField>
                <FormField label="材料">
                  <Textarea
                    placeholder="材料を入力（例: にんじん 1本、玉ねぎ 2個）"
                    value={form.ingredients}
                    onChange={(e) => setForm({ ...form, ingredients: e.target.value })}
                    borderRadius="lg"
                    fontSize="md"
                    rows={3}
                  />
                </FormField>
                <FormField label="作り方">
                  <Textarea
                    placeholder="作り方を入力"
                    value={form.instructions}
                    onChange={(e) => setForm({ ...form, instructions: e.target.value })}
                    borderRadius="lg"
                    fontSize="md"
                    rows={3}
                  />
                </FormField>
                <FormField label="メモ">
                  <Input
                    placeholder="メモ"
                    value={form.memo}
                    onChange={(e) => setForm({ ...form, memo: e.target.value })}
                    size="lg"
                    fontSize="md"
                    borderRadius="lg"
                    minH="48px"
                  />
                </FormField>
                <FormField label="レシピURL">
                  <Input
                    placeholder="https://..."
                    value={form.recipe_url}
                    onChange={(e) => setForm({ ...form, recipe_url: e.target.value })}
                    size="lg"
                    fontSize="md"
                    borderRadius="lg"
                    minH="48px"
                  />
                </FormField>
                <HStack gap={3} pt={2}>
                  <Button
                    type="submit"
                    bg="brand.600"
                    color="white"
                    _hover={{ bg: 'brand.700' }}
                    size="lg"
                    minH="48px"
                    px={8}
                    loading={isSaving}
                    cursor="pointer"
                  >
                    {editingId ? '更新する' : '追加する'}
                  </Button>
                  <Button size="lg" minH="48px" variant="outline" onClick={resetForm} cursor="pointer">
                    キャンセル
                  </Button>
                </HStack>
              </VStack>
            </form>
          </Box>
        </Box>
      )}

      {/* Search + Filters */}
      <Box bg="bg.card" p={5} borderRadius="xl" border="1px solid" borderColor="border.default" mb={6}>
        <VStack gap={4} align="stretch">
          <Input
            placeholder="レシピ名で検索..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            size="lg"
            fontSize="md"
            borderRadius="lg"
            minH="48px"
            bg="white"
          />
          <SimpleGrid columns={{ base: 1, sm: 3 }} gap={3}>
            <Box>
              <Text fontSize="sm" fontWeight="bold" color="text.secondary" mb={1}>カテゴリ</Text>
              <Flex gap={2} flexWrap="wrap">
                {categories.map((cat) => (
                  <Button
                    key={cat.value}
                    size="md"
                    minH="44px"
                    px={4}
                    variant={filterCategory === cat.value ? 'solid' : 'outline'}
                    bg={filterCategory === cat.value ? 'brand.600' : undefined}
                    color={filterCategory === cat.value ? 'white' : 'text.primary'}
                    _hover={{ bg: filterCategory === cat.value ? 'brand.700' : 'brand.50' }}
                    borderRadius="full"
                    onClick={() => { setFilterCategory(cat.value); setPage(1) }}
                    cursor="pointer"
                    fontSize="md"
                  >
                    {cat.value && categoryIcon[cat.value] ? `${categoryIcon[cat.value]} ` : ''}{cat.label}
                  </Button>
                ))}
              </Flex>
            </Box>
            <Box>
              <Text fontSize="sm" fontWeight="bold" color="text.secondary" mb={1}>種類</Text>
              <Flex gap={2} flexWrap="wrap">
                {types.map((t) => (
                  <Button
                    key={t.value}
                    size="md"
                    minH="44px"
                    px={4}
                    variant={filterType === t.value ? 'solid' : 'outline'}
                    bg={filterType === t.value ? 'cyan.600' : undefined}
                    color={filterType === t.value ? 'white' : 'text.primary'}
                    _hover={{ bg: filterType === t.value ? 'cyan.700' : 'cyan.50' }}
                    borderRadius="full"
                    onClick={() => { setFilterType(t.value); setPage(1) }}
                    cursor="pointer"
                    fontSize="md"
                  >
                    {t.label}
                  </Button>
                ))}
              </Flex>
            </Box>
            <Box>
              <Text fontSize="sm" fontWeight="bold" color="text.secondary" mb={1}>難易度</Text>
              <Flex gap={2} flexWrap="wrap">
                {difficulties.map((d) => (
                  <Button
                    key={d.value}
                    size="md"
                    minH="44px"
                    px={4}
                    variant={filterDifficulty === d.value ? 'solid' : 'outline'}
                    bg={filterDifficulty === d.value ? (d.value ? `${difficultyColor[d.value]}.600` : 'gray.600') : undefined}
                    color={filterDifficulty === d.value ? 'white' : 'text.primary'}
                    _hover={{ bg: filterDifficulty === d.value ? undefined : 'gray.50' }}
                    borderRadius="full"
                    onClick={() => { setFilterDifficulty(d.value); setPage(1) }}
                    cursor="pointer"
                    fontSize="md"
                  >
                    {d.label}
                  </Button>
                ))}
              </Flex>
            </Box>
          </SimpleGrid>
          {hasActiveFilters && (
            <Button
              size="md"
              minH="44px"
              variant="ghost"
              color="text.muted"
              onClick={resetFilters}
              cursor="pointer"
              alignSelf="flex-start"
              fontSize="md"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
              フィルターをクリア
            </Button>
          )}
        </VStack>
      </Box>

      {/* Recipe Grid */}
      {isLoading ? (
        <LoadingState type="cards" count={6} />
      ) : !data?.recipes.length ? (
        <EmptyState message={hasActiveFilters ? '条件に一致するレシピがありません' : 'レシピがありません'} icon="search" />
      ) : (
        <>
          <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={6}>
            {data.recipes.map((recipe) => (
              <Box
                key={recipe.id}
                p={6}
                bg="bg.card"
                borderRadius="xl"
                border="1px solid"
                borderColor="border.default"
                _hover={{ borderColor: 'brand.300', shadow: 'md' }}
                transition="all 0.2s"
                cursor="pointer"
                onClick={() => setDetailRecipe(recipe)}
              >
                <VStack align="start" gap={3}>
                  <HStack justify="space-between" w="100%">
                    <Text fontSize="lg" fontWeight="bold" color="text.primary" lineClamp={1}>
                      {recipe.name}
                    </Text>
                    <Text fontSize="lg" flexShrink={0}>
                      {categoryIcon[recipe.category] || '🍽️'}
                    </Text>
                  </HStack>
                  <HStack gap={2} flexWrap="wrap">
                    <Badge colorPalette="blue" variant="subtle" fontSize="sm" px={2} py={0.5}>{recipe.category}</Badge>
                    <Badge colorPalette="cyan" variant="subtle" fontSize="sm" px={2} py={0.5}>{recipe.type}</Badge>
                    <Badge colorPalette={difficultyColor[recipe.difficulty] || 'gray'} variant="subtle" fontSize="sm" px={2} py={0.5}>
                      {recipe.difficulty}
                    </Badge>
                  </HStack>
                  <HStack gap={2} color="text.muted" fontSize="md">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10" />
                      <polyline points="12 6 12 12 16 14" />
                    </svg>
                    <Text>{recipe.cooking_time}分</Text>
                  </HStack>
                  {recipe.ingredients && (
                    <Text fontSize="sm" color="text.muted" lineClamp={2}>
                      {recipe.ingredients}
                    </Text>
                  )}
                </VStack>
              </Box>
            ))}
          </SimpleGrid>

          {data.pagination.total_pages > 1 && (
            <HStack justify="center" mt={8} gap={4}>
              <Button
                size="lg"
                minH="48px"
                variant="outline"
                onClick={() => setPage((p) => p - 1)}
                disabled={!data.pagination.has_prev}
                cursor="pointer"
              >
                前のページ
              </Button>
              <Text fontSize="lg" color="text.secondary" fontWeight="medium">
                {data.pagination.page} / {data.pagination.total_pages}
              </Text>
              <Button
                size="lg"
                minH="48px"
                variant="outline"
                onClick={() => setPage((p) => p + 1)}
                disabled={!data.pagination.has_next}
                cursor="pointer"
              >
                次のページ
              </Button>
            </HStack>
          )}
        </>
      )}

      {/* Recipe Detail Overlay */}
      {detailRecipe && (
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
          onClick={(e) => { if (e.target === e.currentTarget) setDetailRecipe(null) }}
        >
          <Box
            bg="bg.card"
            p={8}
            borderRadius="2xl"
            border="1px solid"
            borderColor="border.default"
            shadow="xl"
            w="100%"
            maxW="640px"
            maxH="90vh"
            overflowY="auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <HStack justify="space-between" mb={4}>
              <Text fontSize="2xl" fontWeight="bold" color="text.primary">
                {detailRecipe.name}
              </Text>
              <Button
                size="md"
                minH="44px"
                minW="44px"
                variant="ghost"
                onClick={() => setDetailRecipe(null)}
                cursor="pointer"
                aria-label="閉じる"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </Button>
            </HStack>

            {/* Badges */}
            <HStack gap={2} mb={5} flexWrap="wrap">
              <Badge colorPalette="blue" variant="subtle" fontSize="md" px={3} py={1}>{detailRecipe.category}</Badge>
              <Badge colorPalette="cyan" variant="subtle" fontSize="md" px={3} py={1}>{detailRecipe.type}</Badge>
              <Badge colorPalette={difficultyColor[detailRecipe.difficulty] || 'gray'} variant="subtle" fontSize="md" px={3} py={1}>
                {detailRecipe.difficulty}
              </Badge>
              <Badge bg="gray.100" color="text.secondary" fontSize="md" px={3} py={1}>
                {detailRecipe.cooking_time}分
              </Badge>
            </HStack>

            {/* Content Sections */}
            <VStack gap={5} align="stretch">
              {detailRecipe.ingredients && (
                <Box>
                  <Text fontSize="md" fontWeight="bold" color="text.secondary" mb={2}>材料</Text>
                  <Box bg="bg.muted" p={4} borderRadius="lg">
                    <Text fontSize="md" color="text.primary" whiteSpace="pre-wrap">{detailRecipe.ingredients}</Text>
                  </Box>
                </Box>
              )}

              {detailRecipe.instructions && (
                <Box>
                  <Text fontSize="md" fontWeight="bold" color="text.secondary" mb={2}>作り方</Text>
                  <Box bg="bg.muted" p={4} borderRadius="lg">
                    <Text fontSize="md" color="text.primary" whiteSpace="pre-wrap">{detailRecipe.instructions}</Text>
                  </Box>
                </Box>
              )}

              {detailRecipe.memo && (
                <Box>
                  <Text fontSize="md" fontWeight="bold" color="text.secondary" mb={2}>メモ</Text>
                  <Box bg="bg.muted" p={4} borderRadius="lg">
                    <Text fontSize="md" color="text.primary">{detailRecipe.memo}</Text>
                  </Box>
                </Box>
              )}

              {detailRecipe.recipe_url && (
                <Box>
                  <Text fontSize="md" fontWeight="bold" color="text.secondary" mb={2}>レシピURL</Text>
                  <a
                    href={detailRecipe.recipe_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: 'var(--chakra-colors-brand-600)', fontSize: 'var(--chakra-fontSizes-md)' }}
                  >
                    {detailRecipe.recipe_url}
                  </a>
                </Box>
              )}

              {/* Structured Ingredients */}
              <IngredientsEditor recipeId={detailRecipe.id} recipeName={detailRecipe.name} />
            </VStack>

            {/* Actions */}
            <HStack gap={3} pt={6} borderTop="1px solid" borderColor="border.default" mt={6}>
              <Button
                size="lg"
                minH="48px"
                px={6}
                bg="brand.600"
                color="white"
                _hover={{ bg: 'brand.700' }}
                onClick={() => startEdit(detailRecipe)}
                cursor="pointer"
                flex={1}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                </svg>
                編集する
              </Button>
              <Button
                size="lg"
                minH="48px"
                px={6}
                colorPalette="red"
                variant="outline"
                onClick={() => setDeleteTarget(detailRecipe.id)}
                cursor="pointer"
              >
                削除
              </Button>
            </HStack>
          </Box>
        </Box>
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget)}
        title="レシピを削除"
        message="このレシピを削除しますか？この操作は取り消せません。"
        loading={deleteMutation.isPending}
      />
    </Box>
  )
}
