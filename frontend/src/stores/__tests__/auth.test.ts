import { describe, it, expect, beforeEach } from 'vitest'
import { useAuthStore } from '../auth'

const mockUser = {
  id: 'user-1',
  email: 'test@test.com',
  full_name: 'テスト太郎',
  role: 'senior',
}

describe('useAuthStore', () => {
  beforeEach(() => {
    // ストアをリセット
    useAuthStore.getState().logout()
  })

  describe('初期状態', () => {
    it('未認証状態であること', () => {
      const state = useAuthStore.getState()
      expect(state.accessToken).toBeNull()
      expect(state.refreshToken).toBeNull()
      expect(state.user).toBeNull()
      expect(state.isAuthenticated).toBe(false)
    })
  })

  describe('setAuth', () => {
    it('トークンとユーザー情報を設定できること', () => {
      useAuthStore.getState().setAuth('access-token', 'refresh-token', mockUser)

      const state = useAuthStore.getState()
      expect(state.accessToken).toBe('access-token')
      expect(state.refreshToken).toBe('refresh-token')
      expect(state.user).toEqual(mockUser)
      expect(state.isAuthenticated).toBe(true)
    })

    it('isAuthenticated が true になること', () => {
      useAuthStore.getState().setAuth('token', 'refresh', mockUser)
      expect(useAuthStore.getState().isAuthenticated).toBe(true)
    })
  })

  describe('logout', () => {
    it('全状態がクリアされること', () => {
      // 先にログイン
      useAuthStore.getState().setAuth('access-token', 'refresh-token', mockUser)
      expect(useAuthStore.getState().isAuthenticated).toBe(true)

      // ログアウト
      useAuthStore.getState().logout()

      const state = useAuthStore.getState()
      expect(state.accessToken).toBeNull()
      expect(state.refreshToken).toBeNull()
      expect(state.user).toBeNull()
      expect(state.isAuthenticated).toBe(false)
    })
  })
})
