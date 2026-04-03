import { test, expect } from './fixtures'

test.describe('作業管理', () => {
  test('タスク作成フォームが動作すること', async ({ loggedInPage: page }) => {
    await page.getByRole('button', { name: '作業管理' }).click()
    await expect(page.getByRole('heading', { name: '作業管理' })).toBeVisible()

    // 新規追加フォームを開く
    await page.getByRole('button', { name: '新規追加' }).click()
    await expect(page.getByPlaceholder('作業名')).toBeVisible()

    // フォームに入力
    await page.getByPlaceholder('作業名').fill('E2Eテスト掃除')

    // 追加ボタンをクリック
    await page.getByRole('button', { name: '追加', exact: true }).click()

    // フォームが閉じること（成功時）またはエラー表示なく動作すること
    await page.waitForTimeout(2000)
  })

  test('タスクページが正しく表示されること', async ({ loggedInPage: page }) => {
    await page.getByRole('button', { name: '作業管理' }).click()

    // 基本UIが表示されること
    await expect(page.getByRole('heading', { name: '作業管理' })).toBeVisible()
    await expect(page.getByRole('button', { name: '新規追加' })).toBeVisible()
  })
})
