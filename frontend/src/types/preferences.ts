export interface UserPreferencesRead {
  theme_id: string | null
  font_size_override: string | null
}

export interface UserPreferencesUpdate {
  theme_id?: string
  font_size_override?: string
}
