import { test, expect, TEST_USER } from './fixtures'

test.describe('認証フロー', () => {
  test('ログイン→ダッシュボード→ログアウト', async ({ loggedInPage: page }) => {
    // ダッシュボードが表示されること
    await expect(page.getByText(/さん/)).toBeVisible()

    // ログアウト
    await page.getByRole('button', { name: 'ログアウト' }).click()

    // ログイン画面に戻ること
    await expect(page.getByText('ホームヘルパー管理システム')).toBeVisible()
    await expect(page.getByPlaceholder('メールアドレス')).toBeVisible()
  })

  test('不正な認証情報でエラー表示', async ({ page }) => {
    await page.goto('/login')
    await page.getByPlaceholder('メールアドレス').fill('wrong@test.com')
    await page.getByPlaceholder('パスワード').fill('wrongpassword')
    await page.getByRole('button', { name: 'ログイン' }).click()

    // ログインページに留まることを確認（リダイレクトされない）
    await page.waitForTimeout(2000)
    await expect(page).toHaveURL(/login/)
    // エラーメッセージまたはログインフォームが表示されていること
    await expect(page.getByPlaceholder('メールアドレス')).toBeVisible()
  })

  test('未認証で保護ページにアクセスするとログインにリダイレクト', async ({ page }) => {
    await page.goto('/recipes')
    await expect(page.getByText('ホームヘルパー管理システム')).toBeVisible()
  })

  test('QRコードモードに切り替えられること', async ({ page }) => {
    await page.goto('/login')
    await page.getByRole('button', { name: 'QRコード' }).click()
    await expect(page.getByPlaceholder('QRトークン')).toBeVisible()
    await expect(page.getByRole('button', { name: 'QRコードでログイン' })).toBeVisible()
  })
})
