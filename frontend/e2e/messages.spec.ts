import { test, expect } from './fixtures'

test.describe('メッセージ', () => {
  test('メッセージページが正しく表示されること', async ({ loggedInPage: page }) => {
    await page.getByRole('button', { name: 'メッセージ' }).click()

    await expect(page.getByRole('heading', { name: 'メッセージ' })).toBeVisible()
    await expect(page.getByPlaceholder('相手のユーザーIDを入力')).toBeVisible()
    await expect(page.getByPlaceholder('メッセージを入力...')).toBeVisible()
    await expect(page.getByRole('button', { name: '送信' })).toBeVisible()
  })

  test('メッセージ送信フロー', async ({ loggedInPage: page, seniorUserId }) => {
    await page.getByRole('button', { name: 'メッセージ' }).click()

    // パートナーID入力
    await page.getByPlaceholder('相手のユーザーIDを入力').fill(seniorUserId)

    // メッセージ送信
    await page.getByPlaceholder('メッセージを入力...').fill('E2Eテストメッセージ')
    await page.getByRole('button', { name: '送信' }).click()

    // 送信後にメッセージが表示されること
    await expect(page.getByText('E2Eテストメッセージ').first()).toBeVisible({ timeout: 5000 })
  })
})
