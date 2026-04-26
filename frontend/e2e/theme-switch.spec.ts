import { test, expect } from './fixtures'

/**
 * ユーザーによるテーマ切替 E2E シナリオ。
 * docs/theme_system_implementation_plan.md §5.4
 *
 * 前提:
 * - バックエンドが起動しており、4 プリセットテーマがシード済みであること
 * - default_theme_id が "standard" であること
 */
test.describe('テーマ切替(一般ユーザー)', () => {
  test('ProfilePage でテーマを変更でき、即座に反映されること', async ({ loggedInPage: page }) => {
    // ProfilePage へ遷移
    await page.goto('/profile')
    await expect(page.getByRole('heading', { name: 'プロファイル' })).toBeVisible()

    // テーマセクションが表示されること
    await expect(page.getByRole('heading', { name: '表示テーマ' })).toBeVisible()

    // テーマカードが 4 枚(全プリセット)見えること
    const radioGroup = page.getByRole('radiogroup', { name: /表示テーマ/ })
    const cards = radioGroup.getByRole('radio')
    await expect(cards).toHaveCount(4)

    // "温もり"(warm)を選択
    await page.getByRole('radio', { name: /温もり/ }).click()

    // トースト成功メッセージ
    await expect(page.getByText('テーマを変更しました')).toBeVisible({ timeout: 5000 })

    // リロードしても変更が維持されていること
    await page.reload()
    await expect(page.getByRole('radio', { name: /温もり/ })).toHaveAttribute('aria-checked', 'true')
  })

  test('キーボードでテーマカード間を移動できること', async ({ loggedInPage: page }) => {
    await page.goto('/profile')

    const standardCard = page.getByRole('radio', { name: /スタンダード/ })
    await standardCard.focus()

    // Space で選択
    await page.keyboard.press(' ')
    await expect(page.getByText('テーマを変更しました')).toBeVisible({ timeout: 5000 })
  })
})
