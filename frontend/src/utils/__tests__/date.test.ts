import { describe, it, expect, vi, afterEach } from 'vitest'
import { toLocalDateString } from '../date'

describe('toLocalDateString', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('YYYY-MM-DD形式で返すこと', () => {
    const date = new Date(2026, 3, 7) // 2026-04-07 (monthは0始まり)
    expect(toLocalDateString(date)).toBe('2026-04-07')
  })

  it('月・日が1桁の場合ゼロ埋めすること', () => {
    const date = new Date(2026, 0, 5) // 2026-01-05
    expect(toLocalDateString(date)).toBe('2026-01-05')
  })

  it('月末の日付を正しく処理すること', () => {
    const date = new Date(2026, 11, 31) // 2026-12-31
    expect(toLocalDateString(date)).toBe('2026-12-31')
  })

  it('年初の日付を正しく処理すること', () => {
    const date = new Date(2026, 0, 1) // 2026-01-01
    expect(toLocalDateString(date)).toBe('2026-01-01')
  })

  it('引数なしの場合、現在日付を返すこと', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 3, 7, 10, 30, 0))
    expect(toLocalDateString()).toBe('2026-04-07')
  })

  it('toISOStringと異なりローカル日付を使用すること', () => {
    // JST午前1時 = UTC前日16時 → toISOStringだと前日になるケース
    // new Date(year, month, day, hour)はローカルタイムで生成される
    const date = new Date(2026, 3, 7, 1, 0, 0) // ローカル 2026-04-07 01:00
    const localResult = toLocalDateString(date)
    const isoResult = date.toISOString().split('T')[0]

    // ローカル日付は常に2026-04-07
    expect(localResult).toBe('2026-04-07')

    // toISOStringはUTC変換するため、UTC+のタイムゾーンでは前日になりうる
    // テスト環境のTZに依存するが、関数の意図を検証
    expect(localResult).toBe(
      `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`,
    )
  })

  it('うるう年の2月29日を正しく処理すること', () => {
    const date = new Date(2028, 1, 29) // 2028-02-29
    expect(toLocalDateString(date)).toBe('2028-02-29')
  })
})
