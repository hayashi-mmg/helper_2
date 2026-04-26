import { test as base, expect, Page, APIRequestContext } from '@playwright/test'

const API_URL = 'http://localhost:8000/api/v1'

export const TEST_USER = {
  email: 'e2e-helper@test.com',
  password: 'e2epassword123',
  full_name: 'E2Eヘルパー',
  role: 'helper',
}

export const TEST_SENIOR = {
  email: 'e2e-senior@test.com',
  password: 'e2epassword123',
  full_name: 'E2E利用者',
  role: 'senior',
}

export const TEST_ADMIN = {
  email: 'e2e-admin@test.com',
  password: 'e2epassword123',
  full_name: 'E2E管理者',
  role: 'system_admin',
}

/**
 * APIを直接呼んでユーザーを登録する（既に存在する場合はログインする）
 * request context を使い、page.request の接続問題を回避
 */
async function ensureUser(request: APIRequestContext, user: typeof TEST_USER): Promise<string> {
  // 登録を試みる
  try {
    const registerRes = await request.post(`${API_URL}/auth/register`, {
      data: {
        email: user.email,
        password: user.password,
        full_name: user.full_name,
        role: user.role,
      },
    })

    if (registerRes.ok()) {
      const data = await registerRes.json()
      return data.user.id
    }
  } catch {
    // ignore
  }

  // 既に存在する場合はログインしてIDを取得
  const loginRes = await request.post(`${API_URL}/auth/login`, {
    data: { email: user.email, password: user.password },
  })
  const data = await loginRes.json()
  return data.user.id
}

/**
 * ブラウザ上でログインする
 */
async function loginViaUI(page: Page, email: string, password: string) {
  await page.goto('/login')
  await page.getByPlaceholder('メールアドレス').fill(email)
  await page.getByPlaceholder('パスワード').fill(password)
  await page.getByRole('button', { name: 'ログイン' }).click()
  // ダッシュボードに遷移するまで待機
  await page.waitForURL('/', { timeout: 10000 })
}

// カスタムフィクスチャ付きテスト
export const test = base.extend<{
  loggedInPage: Page
  adminPage: Page
  seniorUserId: string
}>({
  loggedInPage: async ({ page, request }, use) => {
    await ensureUser(request, TEST_USER)
    await loginViaUI(page, TEST_USER.email, TEST_USER.password)
    await use(page)
  },
  adminPage: async ({ page, request }, use) => {
    await ensureUser(request, TEST_ADMIN)
    await loginViaUI(page, TEST_ADMIN.email, TEST_ADMIN.password)
    await use(page)
  },
  seniorUserId: async ({ request }, use) => {
    const id = await ensureUser(request, TEST_SENIOR)
    await use(id)
  },
})

export { expect }
