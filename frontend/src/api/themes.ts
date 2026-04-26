import client from './client'
import type { ThemeRead, ThemeSummary } from '@/types/theme'

export interface ThemeListResponse {
  themes: ThemeSummary[]
}

export interface ThemeCreatePayload {
  theme_key: string
  name: string
  description?: string
  definition: Record<string, unknown>
  is_active?: boolean
}

export interface ThemeUpdatePayload {
  name?: string
  description?: string
  definition?: Record<string, unknown>
  is_active?: boolean
}

export const themesApi = {
  getPublicDefault: async (): Promise<ThemeRead> => {
    const { data } = await client.get<ThemeRead>('/themes/public/default')
    return data
  },

  list: async (params?: { is_builtin?: boolean; is_active?: boolean }): Promise<ThemeListResponse> => {
    const { data } = await client.get<ThemeListResponse>('/themes', { params })
    return data
  },

  get: async (themeKey: string): Promise<ThemeRead> => {
    const { data } = await client.get<ThemeRead>(`/themes/${themeKey}`)
    return data
  },

  create: async (payload: ThemeCreatePayload): Promise<ThemeRead> => {
    const { data } = await client.post<ThemeRead>('/admin/themes', payload)
    return data
  },

  update: async (themeKey: string, payload: ThemeUpdatePayload): Promise<ThemeRead> => {
    const { data } = await client.put<ThemeRead>(`/admin/themes/${themeKey}`, payload)
    return data
  },

  remove: async (themeKey: string): Promise<void> => {
    await client.delete(`/admin/themes/${themeKey}`)
  },

  setDefault: async (themeKey: string): Promise<void> => {
    await client.put('/admin/settings/default_theme_id', { value: themeKey })
  },
}
