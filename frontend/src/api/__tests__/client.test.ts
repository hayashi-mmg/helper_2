import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useAuthStore } from '@/stores/auth'

// client をテスト前にインポート（axiosの設定を確認）
import client from '../client'

const mockUser = {
  id: 'user-1',
  email: 'test@test.com',
  full_name: 'テスト太郎',
  role: 'senior',
}

describe('API client', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
  })

  describe('設定', () => {
    it('Content-Type が application/json であること', () => {
      expect(client.defaults.headers['Content-Type']).toBe('application/json')
    })
  })

  describe('リクエストインターセプター', () => {
    it('認証済みの場合 Authorization ヘッダーが付与されること', async () => {
      useAuthStore.getState().setAuth('test-access-token', 'test-refresh', mockUser)

      // インターセプターを通してヘッダーを検証
      const config = { headers: {} as Record<string, string> }
      const interceptor = client.interceptors.request.handlers[0]
      const result = await interceptor.fulfilled(config)

      expect(result.headers.Authorization).toBe('Bearer test-access-token')
    })

    it('未認証の場合 Authorization ヘッダーが付与されないこと', async () => {
      const config = { headers: {} as Record<string, string> }
      const interceptor = client.interceptors.request.handlers[0]
      const result = await interceptor.fulfilled(config)

      expect(result.headers.Authorization).toBeUndefined()
    })
  })
})
