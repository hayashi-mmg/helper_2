import { test, expect } from './fixtures'

/**
 * システム既定テーマの変更 E2E シナリオ。
 * docs/theme_system_implementation_plan.md §5.4
 */
test.describe('システム既定テーマ変更', () => {
  test('管理者が既定テーマを変更すると未ログイン画面に反映されること', async ({ adminPage: page, browser }) => {
    await page.goto('/admin/themes')

    // 任意のプリセット(warm 以外の初期状態から warm に)を既定に設定
    const warmRow = page.getByRole('row').filter({ hasText: 'warm' })
    await warmRow.getByRole('button', { name: '既定に設定' }).click()
    await page.getByRole('button', { name: '設定' }).click() // ConfirmDialog の確定ボタン

    // 成功トースト
    await expect(page.getByText('既定テーマを変更しました')).toBeVisible({ timeout: 5000 })

    // 別コンテキスト(未ログイン)で /themes/public/default を叩いて確認
    const fresh = await browser.newContext()
    const apiResp = await fresh.request.get('http://localhost:8000/api/v1/themes/public/default')
    expect(apiResp.ok()).toBe(true)
    const body = await apiResp.json()
    expect(body.theme_key).toBe('warm')

    // 元に戻す(他テストへの影響を避ける)
    await fresh.close()
    const standardRow = page.getByRole('row').filter({ hasText: 'standard' })
    await standardRow.getByRole('button', { name: '既定に設定' }).click()
    await page.getByRole('button', { name: '設定' }).click()
  })
})
