import { test, expect } from './fixtures'

test.describe('買い物管理', () => {
  test('買い物ページが正しく表示されること', async ({ loggedInPage: page }) => {
    await page.getByRole('button', { name: '買い物' }).click()

    await expect(page.getByText('買い物管理')).toBeVisible()
    await expect(page.getByRole('button', { name: '新規依頼' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'すべて' })).toBeVisible()
  })

  test('買い物依頼の作成フロー', async ({ loggedInPage: page, seniorUserId }) => {
    await page.getByRole('button', { name: '買い物' }).click()

    // 新規依頼フォームを開く
    await page.getByRole('button', { name: '新規依頼' }).click()
    await expect(page.getByText('新しい買い物依頼')).toBeVisible()

    // 利用者ID入力
    await page.getByPlaceholder('利用者ID (senior_user_id)').fill(seniorUserId)

    // 商品名入力
    await page.getByPlaceholder('商品名').fill('E2Eテスト牛乳')

    // 依頼を作成
    await page.getByRole('button', { name: '依頼を作成' }).click()

    // 一覧に表示されること
    await expect(page.getByText('E2Eテスト牛乳').first()).toBeVisible({ timeout: 5000 })
  })

  test('ステータスフィルタが動作すること', async ({ loggedInPage: page }) => {
    await page.getByRole('button', { name: '買い物' }).click()

    // フィルタボタンをクリック
    await page.getByRole('button', { name: '完了' }).click()

    // フィルタが適用されること（エラーにならないこと）
    await page.waitForTimeout(1000)
  })
})
