import client from './client'
import type { WeeklyMenuResponse, MealSlotUpdate } from '@/types'

export async function getWeeklyMenu(date?: string): Promise<WeeklyMenuResponse> {
  const { data } = await client.get<WeeklyMenuResponse>('/menus/week', {
    params: date ? { date } : undefined,
  })
  return data
}

export async function updateWeeklyMenu(
  weekStart: string,
  menus: Record<string, MealSlotUpdate>,
): Promise<WeeklyMenuResponse> {
  const { data } = await client.put<WeeklyMenuResponse>('/menus/week', {
    week_start: weekStart,
    menus,
  })
  return data
}

export async function copyWeeklyMenu(
  sourceWeek: string,
  targetWeek: string,
): Promise<WeeklyMenuResponse> {
  const { data } = await client.post<WeeklyMenuResponse>('/menus/week/copy', {
    source_week: sourceWeek,
    target_week: targetWeek,
  })
  return data
}

export async function clearWeeklyMenu(weekStart: string): Promise<void> {
  await client.post('/menus/week/clear', { week_start: weekStart })
}
