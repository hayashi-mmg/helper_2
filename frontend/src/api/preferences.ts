import client from './client'
import type { UserPreferencesRead, UserPreferencesUpdate } from '@/types/preferences'

export const preferencesApi = {
  getMine: async (): Promise<UserPreferencesRead> => {
    const { data } = await client.get<UserPreferencesRead>('/users/me/preferences')
    return data
  },

  updateMine: async (payload: UserPreferencesUpdate): Promise<UserPreferencesRead> => {
    const { data } = await client.put<UserPreferencesRead>('/users/me/preferences', payload)
    return data
  },
}
