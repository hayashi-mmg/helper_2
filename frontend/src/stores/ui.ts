import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface UIState {
  themeId: string | null
  pendingThemeId: string | null
  fontSize: 'normal' | 'large' | 'x-large'
  setThemeId: (id: string | null) => void
  setPendingThemeId: (id: string | null) => void
  setFontSize: (size: 'normal' | 'large' | 'x-large') => void
}

// 旧 LocalStorage キー (theme: 'light'|'dark'|'high-contrast') の互換マッピング。
// 初回起動時のみ実行し、API 側の値が正となる。
function migrateLegacyTheme(): string | null {
  try {
    const raw = localStorage.getItem('ui-legacy-theme')
    if (!raw) return null
    if (raw === 'high-contrast') return 'high-contrast'
    return 'standard'
  } catch {
    return null
  }
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      themeId: migrateLegacyTheme(),
      pendingThemeId: null,
      fontSize: 'normal',
      setThemeId: (id) => set({ themeId: id, pendingThemeId: null }),
      setPendingThemeId: (id) => set({ pendingThemeId: id }),
      setFontSize: (size) => set({ fontSize: size }),
    }),
    { name: 'ui-storage' },
  ),
)
