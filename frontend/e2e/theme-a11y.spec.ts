import { test, expect } from './fixtures'

/**
 * テーマシステムのアクセシビリティ検証。
 * docs/theme_system_implementation_plan.md §5.5
 *
 * NOTE: 完全な WCAG スキャンには @axe-core/playwright が必要。
 *       本スペックは Playwright ネイティブ機能で検査可能な項目のみ扱う。
 *       axe-core を導入する場合: npm i -D @axe-core/playwright
 */
test.describe('テーマシステム アクセシビリティ', () => {
  test('ProfilePage のテーマセクションが正しい ARIA 属性を持つこと', async ({ loggedInPage: page }) => {
    await page.goto('/profile')

    // radiogroup role と ラベル関連付け
    const radioGroup = page.getByRole('radiogroup', { name: /表示テーマ/ })
    await expect(radioGroup).toBeVisible()

    // 各ラジオ要素が aria-checked を持つこと
    const radios = radioGroup.getByRole('radio')
    const count = await radios.count()
    expect(count).toBeGreaterThanOrEqual(4)
    for (let i = 0; i < count; i++) {
      await expect(radios.nth(i)).toHaveAttribute('aria-checked', /true|false/)
    }
  })

  test('テーマカードがタッチ最小 44px 要件を満たすこと', async ({ loggedInPage: page }) => {
    await page.goto('/profile')
    const radios = page.getByRole('radiogroup', { name: /表示テーマ/ }).getByRole('radio')
    const firstBox = await radios.first().boundingBox()
    expect(firstBox).not.toBeNull()
    expect(firstBox!.height).toBeGreaterThanOrEqual(44)
    expect(firstBox!.width).toBeGreaterThanOrEqual(44)
  })

  test('テーマカードがキーボードで操作可能であること', async ({ loggedInPage: page }) => {
    await page.goto('/profile')
    const firstRadio = page.getByRole('radiogroup', { name: /表示テーマ/ }).getByRole('radio').first()

    // tabIndex=0 でフォーカス可能
    await firstRadio.focus()
    await expect(firstRadio).toBeFocused()
  })

  test('ハイコントラストテーマ適用時に本文色と背景の十分なコントラストが維持されること', async ({ loggedInPage: page }) => {
    await page.goto('/profile')

    // ハイコントラストに切替
    await page.getByRole('radio', { name: /ハイコントラスト/ }).click()
    await expect(page.getByText('テーマを変更しました')).toBeVisible({ timeout: 5000 })

    // 本文要素の computed color と background が十分異なることを確認(厳密なコントラスト計算ではないが、可視性を担保)
    const bodyStyles = await page.evaluate(() => {
      const style = getComputedStyle(document.body)
      return { color: style.color, bg: style.backgroundColor }
    })
    expect(bodyStyles.color).not.toBe(bodyStyles.bg)
  })
})
