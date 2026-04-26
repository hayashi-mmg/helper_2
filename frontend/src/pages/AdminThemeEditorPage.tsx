import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Box,
  Button,
  HStack,
  Input,
  SimpleGrid,
  Text,
  Textarea,
  VStack,
} from '@chakra-ui/react'
import { themesApi } from '@/api/themes'
import PageHeader from '@/components/ui/PageHeader'
import FormField from '@/components/ui/FormField'
import LoadingState from '@/components/ui/LoadingState'
import { toaster } from '@/components/ui/toaster'
import { validateThemeDefinition } from '@/theme/validateThemeDefinition'
import { standardPreset } from '@/theme/presets/standard'
import ContrastBadge from '@/components/theme/ContrastBadge'
import ThemePreview from '@/components/theme/ThemePreview'
import type { ThemeDefinition, ThemeValidationError } from '@/types/theme'

interface Props {
  mode: 'new' | 'edit'
}

function resolveColor(definition: ThemeDefinition, value: string | undefined): string {
  if (!value) return '#000000'
  if (value.startsWith('#')) return value
  const m = value.match(/^\{colors\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\}$/)
  if (!m) return '#000000'
  const [, palette, shade] = m
  const paletteObj = (definition.colors as unknown as Record<string, Record<string, string>>)[palette]
  return paletteObj?.[shade] ?? '#000000'
}

function ContrastBadgeGroup({ definition }: { definition: ThemeDefinition }) {
  const tokens = definition.semanticTokens ?? {}
  const textPrimary = resolveColor(definition, tokens['text.primary'])
  const bgPage = resolveColor(definition, tokens['bg.page'])
  const textOnBrand = resolveColor(definition, tokens['text.onBrand'])
  const brand500 = definition.colors.brand['500']
  const borderFocus = resolveColor(definition, tokens['border.focus'])

  return (
    <VStack align="stretch" gap={2}>
      <ContrastBadge label="本文 vs 背景" fg={textPrimary} bg={bgPage} minRatio={4.5} />
      <ContrastBadge label="ブランド上テキスト" fg={textOnBrand} bg={brand500} minRatio={4.5} />
      <ContrastBadge label="フォーカス枠 vs 背景" fg={borderFocus} bg={bgPage} minRatio={3.0} />
    </VStack>
  )
}

/**
 * 管理者用テーマ登録/編集画面。
 * docs/admin_management_specification.md §12.2
 */
export default function AdminThemeEditorPage({ mode }: Props) {
  const { themeKey: routeKey } = useParams<{ themeKey: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [themeKey, setThemeKey] = useState('')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [definitionJson, setDefinitionJson] = useState(() =>
    JSON.stringify(standardPreset, null, 2),
  )
  const [clientErrors, setClientErrors] = useState<ThemeValidationError[]>([])
  const [serverErrors, setServerErrors] = useState<ThemeValidationError[]>([])

  // 編集モード: 既存テーマを取得
  const existingQuery = useQuery({
    queryKey: ['themes', 'admin-detail', routeKey],
    queryFn: () => themesApi.get(routeKey!),
    enabled: mode === 'edit' && !!routeKey,
  })

  useEffect(() => {
    if (existingQuery.data) {
      const t = existingQuery.data
      setThemeKey(t.theme_key)
      setName(t.name)
      setDescription(t.description ?? '')
      setIsActive(t.is_active)
      setDefinitionJson(JSON.stringify(t.definition, null, 2))
    }
  }, [existingQuery.data])

  const isBuiltin = existingQuery.data?.is_builtin ?? false

  // リアルタイムバリデーション(入力変更のたびに)
  const parsedResult = useMemo(() => {
    try {
      const parsed = JSON.parse(definitionJson)
      return validateThemeDefinition(parsed)
    } catch (e) {
      return {
        ok: false as const,
        errors: [
          {
            field: 'definition',
            code: 'invalid_json',
            message: `JSON 形式が不正です: ${(e as Error).message}`,
          },
        ],
      }
    }
  }, [definitionJson])

  useEffect(() => {
    if (!parsedResult.ok) {
      setClientErrors(parsedResult.errors)
    } else {
      setClientErrors([])
    }
  }, [parsedResult])

  const createMutation = useMutation({
    mutationFn: () =>
      themesApi.create({
        theme_key: themeKey,
        name,
        description: description || undefined,
        definition: JSON.parse(definitionJson),
        is_active: isActive,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['themes'] })
      toaster.success({ title: 'テーマを登録しました' })
      navigate('/admin/themes')
    },
    onError: (err: {
      response?: { data?: { detail?: { code?: string; errors?: ThemeValidationError[]; message?: string } } }
    }) => {
      const detail = err.response?.data?.detail
      if (detail?.errors) {
        setServerErrors(detail.errors)
      } else {
        toaster.error({ title: detail?.message ?? '登録に失敗しました' })
      }
    },
  })

  const updateMutation = useMutation({
    mutationFn: () =>
      themesApi.update(routeKey!, {
        name,
        description: description || undefined,
        definition: isBuiltin ? undefined : JSON.parse(definitionJson),
        is_active: isActive,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['themes'] })
      toaster.success({ title: 'テーマを更新しました' })
      navigate('/admin/themes')
    },
    onError: (err: {
      response?: { data?: { detail?: { code?: string; errors?: ThemeValidationError[]; message?: string } } }
    }) => {
      const detail = err.response?.data?.detail
      if (detail?.errors) {
        setServerErrors(detail.errors)
      } else {
        toaster.error({ title: detail?.message ?? '更新に失敗しました' })
      }
    },
  })

  const handleSubmit = () => {
    setServerErrors([])
    if (!isBuiltin && !parsedResult.ok) return
    if (mode === 'new') createMutation.mutate()
    else updateMutation.mutate()
  }

  if (mode === 'edit' && existingQuery.isLoading) {
    return <LoadingState type="form" count={4} />
  }

  const errors = [...clientErrors, ...serverErrors]
  const canSubmit =
    !!name &&
    !!themeKey &&
    (isBuiltin || parsedResult.ok)

  return (
    <Box>
      <PageHeader title={mode === 'new' ? 'テーマ登録' : `テーマ編集: ${themeKey}`} />

      <Box bg="bg.card" borderRadius="xl" border="1px solid" borderColor="border.default" p={6} maxW="1200px">
        <VStack align="stretch" gap={4}>
          <FormField label="テーマキー" required>
            <Input
              value={themeKey}
              onChange={(e) => setThemeKey(e.target.value)}
              placeholder="custom_a"
              disabled={mode === 'edit'}
              size="lg"
            />
          </FormField>

          <FormField label="名前" required>
            <Input value={name} onChange={(e) => setName(e.target.value)} size="lg" />
          </FormField>

          <FormField label="説明">
            <Input value={description} onChange={(e) => setDescription(e.target.value)} size="lg" />
          </FormField>

          <FormField label="有効">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              style={{ width: '24px', height: '24px' }}
            />
          </FormField>

          <SimpleGrid columns={{ base: 1, lg: 2 }} gap={6}>
            <FormField label={`定義 JSON${isBuiltin ? '(組込みテーマは変更不可)' : ''}`}>
              <Textarea
                value={definitionJson}
                onChange={(e) => setDefinitionJson(e.target.value)}
                rows={24}
                fontFamily="mono"
                fontSize="sm"
                readOnly={isBuiltin}
                bg={isBuiltin ? 'bg.subtle' : undefined}
              />
            </FormField>

            <VStack align="stretch" gap={4}>
              <Text fontWeight="bold">プレビューとコントラスト比</Text>
              <ThemePreview definition={parsedResult.ok ? (parsedResult.parsed as ThemeDefinition) : null} />
              {parsedResult.ok && <ContrastBadgeGroup definition={parsedResult.parsed as ThemeDefinition} />}
            </VStack>
          </SimpleGrid>

          {errors.length > 0 && (
            <Box bg="red.50" color="red.700" p={4} borderRadius="md" role="alert">
              <Text fontWeight="bold" mb={2}>
                バリデーションエラー:
              </Text>
              <VStack align="stretch" gap={1}>
                {errors.map((e, idx) => (
                  <Text key={idx} fontSize="sm">
                    <strong>{e.field}</strong>: {e.message}({e.code})
                  </Text>
                ))}
              </VStack>
            </Box>
          )}

          <HStack gap={3} pt={2}>
            <Button
              bg="brand.600"
              color="white"
              size="lg"
              onClick={handleSubmit}
              disabled={!canSubmit}
              loading={createMutation.isPending || updateMutation.isPending}
            >
              保存
            </Button>
            <Button size="lg" variant="outline" onClick={() => navigate('/admin/themes')}>
              キャンセル
            </Button>
          </HStack>
        </VStack>
      </Box>
    </Box>
  )
}
