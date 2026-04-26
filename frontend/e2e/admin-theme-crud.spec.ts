import { test, expect } from './fixtures'

/**
 * 管理者のカスタムテーマ CRUD E2E シナリオ。
 * docs/theme_system_implementation_plan.md §5.4
 *
 * 前提: system_admin ロールの E2E ユーザーが登録可能か、
 * または環境変数 E2E_ADMIN_EMAIL / E2E_ADMIN_PASSWORD で既存管理者を指定できること。
 */
test.describe('管理者テーマ CRUD', () => {
  test('カスタムテーマを登録 → 編集 → 削除できること', async ({ adminPage: page }) => {
    // 一覧ページに遷移
    await page.goto('/admin/themes')
    await expect(page.getByRole('heading', { name: 'テーマ管理' })).toBeVisible()

    // 既存プリセットが見えること(少なくとも standard)
    await expect(page.getByText('standard')).toBeVisible()

    // 「新規登録」をクリック
    await page.getByRole('button', { name: '新規登録' }).click()
    await expect(page.getByRole('heading', { name: 'テーマ登録' })).toBeVisible()

    // テーマキーと名前を入力
    const uniqueKey = `e2e-test-${Date.now()}`
    await page.getByLabel('テーマキー').fill(uniqueKey)
    await page.getByLabel('名前').fill('E2E テスト')
    await page.getByLabel('説明').fill('E2E テストで作成')

    // 定義 JSON は初期値(standard コピー)のまま — id フィールドを更新
    const textarea = page.locator('textarea').first()
    const currentJson = await textarea.inputValue()
    const updatedJson = currentJson.replace('"id": "standard"', `"id": "${uniqueKey}"`)
    await textarea.fill(updatedJson)

    // 保存
    await page.getByRole('button', { name: '保存' }).click()

    // 一覧に戻って新規テーマが見えること
    await expect(page.getByText(uniqueKey)).toBeVisible({ timeout: 10000 })

    // 編集ボタンをクリック
    const row = page.getByRole('row').filter({ hasText: uniqueKey })
    await row.getByRole('button', { name: '編集' }).click()
    await expect(page.getByRole('heading', { name: new RegExp(uniqueKey) })).toBeVisible()

    // 名前を変更して保存
    await page.getByLabel('名前').fill('E2E テスト更新後')
    await page.getByRole('button', { name: '保存' }).click()

    // 一覧で変更が反映されていること
    await expect(page.getByText('E2E テスト更新後')).toBeVisible({ timeout: 10000 })

    // 削除
    const updatedRow = page.getByRole('row').filter({ hasText: uniqueKey })
    await updatedRow.getByRole('button', { name: '削除' }).click()
    await page.getByRole('button', { name: '削除' }).last().click() // ConfirmDialog の削除ボタン

    // 一覧から消えていること
    await expect(page.getByText(uniqueKey)).not.toBeVisible({ timeout: 10000 })
  })

  test('フォントサイズ 17px のテーマは登録できないこと(バリデーション拒否)', async ({ adminPage: page }) => {
    await page.goto('/admin/themes/new')

    const uniqueKey = `e2e-invalid-${Date.now()}`
    await page.getByLabel('テーマキー').fill(uniqueKey)
    await page.getByLabel('名前').fill('無効なテーマ')

    const textarea = page.locator('textarea').first()
    const currentJson = await textarea.inputValue()
    const badJson = currentJson
      .replace('"id": "standard"', `"id": "${uniqueKey}"`)
      .replace('"baseSizePx": 18', '"baseSizePx": 17')
    await textarea.fill(badJson)

    // クライアント側バリデーションでエラー表示
    await expect(page.getByText(/font_size_too_small/)).toBeVisible()

    // 保存ボタンが無効化されていること
    await expect(page.getByRole('button', { name: '保存' })).toBeDisabled()
  })

  test('組込みテーマは削除できないこと', async ({ adminPage: page }) => {
    await page.goto('/admin/themes')

    // standard 行の操作エリアに削除ボタンが存在しないこと
    const standardRow = page.getByRole('row').filter({ hasText: 'standard' })
    await expect(standardRow.getByRole('button', { name: '削除' })).toHaveCount(0)
  })
})
