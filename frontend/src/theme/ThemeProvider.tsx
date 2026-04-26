import React, { useEffect, useMemo } from 'react'
import { ChakraProvider } from '@chakra-ui/react'
import { useQuery } from '@tanstack/react-query'
import { themesApi } from '@/api/themes'
import { preferencesApi } from '@/api/preferences'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import type { ThemeDefinition } from '@/types/theme'
import { buildSystem } from './buildSystem'
import { standardPreset } from './presets/standard'

interface Props {
  children: React.ReactNode
}

/**
 * アプリ全体のテーマを動的に管理する Provider。
 * 仕様: docs/theme_system_specification.md §8、docs/frontend_implementation_plan.md §3.1.0
 */
export function ThemeProvider({ children }: Props) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const setThemeId = useUIStore((s) => s.setThemeId)

  // 未ログイン時: システム既定テーマ
  const publicDefaultQuery = useQuery({
    queryKey: ['themes', 'public-default'],
    queryFn: () => themesApi.getPublicDefault(),
    enabled: !isAuthenticated,
    staleTime: 5 * 60 * 1000,
  })

  // ログイン時: ユーザー設定
  const prefsQuery = useQuery({
    queryKey: ['preferences', 'me'],
    queryFn: () => preferencesApi.getMine(),
    enabled: isAuthenticated,
    staleTime: 60 * 1000,
  })

  const effectiveKey = isAuthenticated
    ? prefsQuery.data?.theme_id ?? publicDefaultQuery.data?.theme_key ?? null
    : publicDefaultQuery.data?.theme_key ?? null

  // テーマ定義
  const themeQuery = useQuery({
    queryKey: ['themes', effectiveKey ?? 'standard'],
    queryFn: () => themesApi.get(effectiveKey!),
    enabled: !!effectiveKey && effectiveKey !== publicDefaultQuery.data?.theme_key,
    staleTime: 5 * 60 * 1000,
  })

  useEffect(() => {
    if (effectiveKey) setThemeId(effectiveKey)
  }, [effectiveKey, setThemeId])

  const definition: ThemeDefinition = useMemo(() => {
    // 優先順位: ユーザー選択テーマの詳細 > 公開既定の定義 > ローカルプリセット
    if (themeQuery.data?.definition) return themeQuery.data.definition
    if (publicDefaultQuery.data?.definition) return publicDefaultQuery.data.definition
    return standardPreset
  }, [themeQuery.data, publicDefaultQuery.data])

  const system = useMemo(() => {
    try {
      return buildSystem(definition)
    } catch (err) {
      // バリデーション失敗時は standard にフォールバック
      // eslint-disable-next-line no-console
      console.warn('[ThemeProvider] buildSystem failed, falling back to standard', err)
      return buildSystem(standardPreset)
    }
  }, [definition])

  return <ChakraProvider value={system}>{children}</ChakraProvider>
}
