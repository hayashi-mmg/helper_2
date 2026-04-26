/**
 * 現在のローカル週次献立を、本番管理画面の「献立インポート」JSON形式に変換する。
 *
 * 1. 表示中の WeeklyMenuResponse から登場するレシピIDを集め、
 * 2. /recipes API でレシピ詳細を取得し、
 * 3. recipe_name 参照ベースの import payload を組み立てる。
 */
import { getRecipe } from '@/api/recipes'
import type { WeeklyMenuResponse } from '@/types'

export interface ExportedMenuJson {
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
}

const DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

export async function buildImportJson(menu: WeeklyMenuResponse): Promise<ExportedMenuJson> {
  // 登場する recipe_id を一意化
  const recipeIds = new Set<string>()
  for (const day of DAYS) {
    const slot = menu.menus[day]
    if (!slot) continue
    for (const meal of ['breakfast', 'dinner'] as const) {
      for (const entry of slot[meal] ?? []) {
        recipeIds.add(entry.recipe.id)
      }
    }
  }

  const recipes = await Promise.all(Array.from(recipeIds).map((id) => getRecipe(id)))

  const idToName = new Map(recipes.map((r) => [r.id, r.name]))

  const exportedMenu: ExportedMenuJson['menu'] = {}
  for (const day of DAYS) {
    const slot = menu.menus[day]
    exportedMenu[day] = {
      breakfast:
        slot?.breakfast.map((e) => ({
          recipe_name: idToName.get(e.recipe.id) ?? e.recipe.name,
          recipe_type: e.recipe_type,
        })) ?? [],
      dinner:
        slot?.dinner.map((e) => ({
          recipe_name: idToName.get(e.recipe.id) ?? e.recipe.name,
          recipe_type: e.recipe_type,
        })) ?? [],
    }
  }

  return {
    week_start: menu.week_start,
    recipes: recipes.map((r) => ({
      name: r.name,
      category: r.category,
      type: r.type,
      difficulty: r.difficulty,
      cooking_time: r.cooking_time,
      ingredients_text: r.ingredients ?? null,
      instructions: r.instructions ?? null,
      memo: r.memo ?? null,
      recipe_url: r.recipe_url ?? null,
    })),
    menu: exportedMenu,
  }
}
