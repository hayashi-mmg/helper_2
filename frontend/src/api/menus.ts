import client from './client'
import type {
  WeeklyMenuResponse,
  MealSlotUpdate,
  MenuSuggestionRequest,
  WeeklyMenuSuggestionResponse,
} from '@/types'

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

export async function suggestMenu(
  req: MenuSuggestionRequest,
): Promise<WeeklyMenuSuggestionResponse> {
  const { data } = await client.post<WeeklyMenuSuggestionResponse>(
    '/menus/suggest',
    req,
    { timeout: 260_000 },
  )
  return data
}

export interface SelfMenuImportPayload {
  week_start: string
  recipes: Array<{
    name: string
    category: string
    type: string
    difficulty: string
    cooking_time: number
    ingredients_text: string | null
    instructions: string | null
    memo: string | null
    recipe_url: string | null
  }>
  menu: Record<
    string,
    {
      breakfast: Array<{ recipe_name: string; recipe_type: string }>
      dinner: Array<{ recipe_name: string; recipe_type: string }>
    }
  >
  generate_shopping_list?: boolean
  dry_run?: boolean
}

export interface SelfMenuImportResponse {
  applied: boolean
  target_user: { id: string; email: string; full_name: string; role: string }
  week_start: string
  created_recipe_count: number
  reused_recipe_count: number
  replaced_menu: boolean
  shopping_list: {
    request_id: string
    total_items: number
    excluded_items: number
    active_items: number
    replaced_existing: boolean
  } | null
  warnings: string[]
}

export async function importSelfMenu(
  payload: SelfMenuImportPayload,
): Promise<SelfMenuImportResponse> {
  const { data } = await client.post<SelfMenuImportResponse>('/menus/import', payload)
  return data
}
