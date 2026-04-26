import { useMemo, useState, type ChangeEvent } from 'react'
import { Box, Button, HStack, Input, Text, Textarea, VStack } from '@chakra-ui/react'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  getAdminUsers,
  importMenu,
  type MenuImportRequest,
  type MenuImportResponse,
} from '@/api/admin'
import FormField from '@/components/ui/FormField'
import PageHeader from '@/components/ui/PageHeader'
import Select from '@/components/ui/Select'
import { toaster } from '@/components/ui/toaster'

interface ApiError {
  response?: { data?: { detail?: string | unknown } }
}

function formatDetail(detail: unknown): string {
  if (!detail) return 'エラーが発生しました'
  if (typeof detail === 'string') return detail
  return JSON.stringify(detail)
}

function nextMonday(): string {
  const today = new Date()
  const offset = (8 - today.getDay()) % 7 || 7  // 0=Sun..6=Sat → next Mon
  const d = new Date(today)
  d.setDate(today.getDate() + offset)
  return d.toISOString().slice(0, 10)
}

type Parsed =
  | { ok: true; payload: Pick<MenuImportRequest, 'recipes' | 'menu' | 'week_start'> }
  | { ok: false; error: string }

function parseJson(text: string): Parsed {
  if (!text.trim()) return { ok: false, error: 'JSONを入力してください' }
  try {
    const obj = JSON.parse(text)
    if (typeof obj !== 'object' || obj === null) {
      return { ok: false, error: 'JSONがオブジェクトではありません' }
    }
    if (!Array.isArray(obj.recipes) || typeof obj.menu !== 'object' || obj.menu === null) {
      return { ok: false, error: 'recipes(配列) と menu(オブジェクト) が必要です' }
    }
    return {
      ok: true,
      payload: {
        recipes: obj.recipes,
        menu: obj.menu,
        week_start: typeof obj.week_start === 'string' ? obj.week_start : '',
      },
    }
  } catch (e) {
    return { ok: false, error: `JSONパースエラー: ${(e as Error).message}` }
  }
}

export default function AdminMenuImportPage() {
  const [targetUserId, setTargetUserId] = useState('')
  const [weekStart, setWeekStart] = useState(nextMonday())
  const [jsonText, setJsonText] = useState('')
  const [generateShoppingList, setGenerateShoppingList] = useState(true)
  const [result, setResult] = useState<MenuImportResponse | null>(null)
  const [resultMode, setResultMode] = useState<'preview' | 'applied' | null>(null)

  const { data: usersData } = useQuery({
    queryKey: ['admin', 'users', 'all-active'],
    queryFn: () => getAdminUsers({ is_active: true, limit: 100 }),
    staleTime: 60_000,
  })

  const userOptions = useMemo(() => {
    const users = usersData?.users ?? []
    return users.map((u) => ({
      value: u.id,
      label: `${u.full_name}（${u.email} / ${u.role}）`,
    }))
  }, [usersData])

  const parsed = useMemo(() => parseJson(jsonText), [jsonText])

  const buildPayload = (dryRun: boolean): MenuImportRequest | null => {
    if (!targetUserId) {
      toaster.create({ title: '対象ユーザーを選択してください', type: 'error' })
      return null
    }
    if (!parsed.ok) {
      toaster.create({ title: parsed.error, type: 'error' })
      return null
    }
    const ws = weekStart || parsed.payload.week_start
    if (!ws) {
      toaster.create({ title: 'week_start を指定してください', type: 'error' })
      return null
    }
    return {
      target_user_id: targetUserId,
      week_start: ws,
      recipes: parsed.payload.recipes,
      menu: parsed.payload.menu,
      generate_shopping_list: generateShoppingList,
      dry_run: dryRun,
    }
  }

  const importMutation = useMutation({
    mutationFn: importMenu,
    onSuccess: (res) => {
      setResult(res)
      setResultMode(res.applied ? 'applied' : 'preview')
      if (res.applied) {
        const shopping = res.shopping_list
          ? `、買い物リスト${res.shopping_list.total_items}件`
          : ''
        toaster.create({
          title: `献立を取り込みました（新規レシピ${res.created_recipe_count}件${shopping}）`,
          type: 'success',
        })
      }
    },
    onError: (err: ApiError) => {
      toaster.create({
        title: formatDetail(err.response?.data?.detail),
        type: 'error',
      })
    },
  })

  const onPreview = () => {
    const p = buildPayload(true)
    if (p) importMutation.mutate(p)
  }

  const onApply = () => {
    const p = buildPayload(false)
    if (p) importMutation.mutate(p)
  }

  const onFileSelected = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    file.text().then((text) => setJsonText(text))
  }

  return (
    <VStack align="stretch" gap={6}>
      <PageHeader title="献立インポート" />

      <Box bg="bg.card" p={6} borderRadius="xl" shadow="sm" border="1px solid" borderColor="border.default">
        <VStack align="stretch" gap={5}>
          <FormField label="対象ユーザー" required>
            <Select
              value={targetUserId}
              onChange={setTargetUserId}
              options={userOptions}
              placeholder="ユーザーを選択..."
            />
          </FormField>

          <FormField label="週開始日（月曜日）" required>
            <Input
              type="date"
              value={weekStart}
              onChange={(e) => setWeekStart(e.target.value)}
              size="lg"
            />
          </FormField>

          <FormField label="献立JSON" required>
            <Textarea
              value={jsonText}
              onChange={(e) => setJsonText(e.target.value)}
              placeholder='{"week_start": "2026-04-27", "recipes": [...], "menu": {"monday": {...}, ...}}'
              rows={16}
              fontFamily="mono"
              fontSize="sm"
            />
            <HStack mt={2}>
              <Input type="file" accept="application/json,.json" onChange={onFileSelected} size="sm" />
              {!parsed.ok && jsonText.trim() && (
                <Text color="red.600" fontSize="sm">{parsed.error}</Text>
              )}
              {parsed.ok && (
                <Text color="text.secondary" fontSize="sm">
                  recipes: {parsed.payload.recipes.length}件 / menu: {Object.keys(parsed.payload.menu).length}日
                </Text>
              )}
            </HStack>
          </FormField>

          <FormField label="買い物リストも自動生成する">
            <input
              type="checkbox"
              checked={generateShoppingList}
              onChange={(e) => setGenerateShoppingList(e.target.checked)}
              style={{ width: '24px', height: '24px' }}
            />
          </FormField>

          <HStack gap={3}>
            <Button onClick={onPreview} loading={importMutation.isPending} variant="outline">
              プレビュー
            </Button>
            <Button onClick={onApply} loading={importMutation.isPending} colorPalette="blue">
              本番に取り込む
            </Button>
          </HStack>
        </VStack>
      </Box>

      {result && (
        <Box
          bg={resultMode === 'applied' ? 'green.50' : 'blue.50'}
          color={resultMode === 'applied' ? 'green.800' : 'blue.800'}
          p={5}
          borderRadius="xl"
          border="1px solid"
          borderColor={resultMode === 'applied' ? 'green.200' : 'blue.200'}
        >
          <Text fontWeight="bold" mb={2}>
            {resultMode === 'applied' ? '取り込み完了' : 'プレビュー（DBは未変更）'}
          </Text>
          <VStack align="stretch" gap={1} fontSize="sm">
            <Text>対象: {result.target_user.full_name}（{result.target_user.email}）</Text>
            <Text>週開始: {result.week_start}</Text>
            <Text>新規レシピ: {result.created_recipe_count}件 / 既存再利用: {result.reused_recipe_count}件</Text>
            <Text>既存週献立の置換: {result.replaced_menu ? 'あり' : 'なし'}</Text>
            {result.shopping_list && (
              <Text>
                買い物リスト: 全{result.shopping_list.total_items}件
                （除外{result.shopping_list.excluded_items}件、購入{result.shopping_list.active_items}件）
                {result.shopping_list.replaced_existing && ' / 既存リスト置換'}
              </Text>
            )}
            {!result.shopping_list && (
              <Text>買い物リスト: 生成なし</Text>
            )}
            {result.warnings.length > 0 && (
              <Box mt={2}>
                <Text fontWeight="semibold">警告:</Text>
                {result.warnings.map((w, i) => (
                  <Text key={i} fontSize="sm">- {w}</Text>
                ))}
              </Box>
            )}
          </VStack>
        </Box>
      )}
    </VStack>
  )
}
