import { test, expect } from './fixtures'

test.describe('ナビゲーション', () => {
  test('全ナビリンクが正しく遷移すること', async ({ loggedInPage: page }) => {
    // レシピ
    await page.getByRole('button', { name: 'レシピ' }).click()
    await expect(page.getByRole('heading', { name: 'レシピ一覧' })).toBeVisible()

    // 献立
    await page.getByRole('button', { name: '献立' }).click()
    await expect(page.getByRole('heading', { name: '週間献立' })).toBeVisible()

    // 作業管理
    await page.getByRole('button', { name: '作業管理' }).click()
    await expect(page.getByRole('heading', { name: '作業管理' })).toBeVisible()

    // メッセージ
    await page.getByRole('button', { name: 'メッセージ' }).click()
    await expect(page.getByRole('heading', { name: 'メッセージ' })).toBeVisible()

    // 買い物
    await page.getByRole('button', { name: '買い物' }).click()
    await expect(page.getByRole('heading', { name: '買い物管理' })).toBeVisible()

    // ダッシュボードに戻る
    await page.getByRole('button', { name: 'ダッシュボード' }).click()
    await expect(page.getByRole('heading', { name: /さん/ })).toBeVisible()
  })

  test('ダッシュボードのカードからページ遷移できること', async ({ loggedInPage: page }) => {
    await page.getByText('レシピ管理').click()
    await expect(page.getByText('レシピ一覧')).toBeVisible()
  })
})
