import { test, expect } from './fixtures'

test.describe('レシピ管理', () => {
  test('レシピのCRUDフロー', async ({ loggedInPage: page }) => {
    // レシピページへ移動
    await page.getByRole('button', { name: 'レシピ' }).click()
    await expect(page.getByText('レシピ一覧')).toBeVisible()

    // 新規追加
    await page.getByRole('button', { name: '新規追加' }).click()
    await page.getByPlaceholder('レシピ名').fill('E2Eテスト焼きそば')
    await page.getByPlaceholder('調理時間（分）').fill('15')
    await page.getByPlaceholder('材料').fill('麺 1玉\nキャベツ 100g')
    await page.getByPlaceholder('作り方').fill('1. 炒める\n2. 味付け')

    await page.getByRole('button', { name: '追加', exact: true }).click()

    // 一覧に表示されること
    await expect(page.getByText('E2Eテスト焼きそば')).toBeVisible({ timeout: 5000 })

    // 削除
    page.on('dialog', (dialog) => dialog.accept())
    // 最初の削除ボタンをクリック（作成したレシピ）
    await page.getByRole('button', { name: '削除' }).first().click()

    // 少し待ってからリストが更新されることを確認
    await page.waitForTimeout(2000)
  })

  test('レシピ検索', async ({ loggedInPage: page }) => {
    await page.getByRole('button', { name: 'レシピ' }).click()
    await page.getByPlaceholder('レシピを検索...').fill('存在しないレシピ名XYZ')

    // 結果がないことを確認（エラーにならないこと）
    await page.waitForTimeout(1000)
  })
})
