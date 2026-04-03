import client from './client'
import type { RecipeIngredientsResponse, RecipeIngredientInput } from '@/types'

export async function getRecipeIngredients(recipeId: string): Promise<RecipeIngredientsResponse> {
  const { data } = await client.get<RecipeIngredientsResponse>(`/recipes/${recipeId}/ingredients`)
  return data
}

export async function updateRecipeIngredients(
  recipeId: string,
  ingredients: RecipeIngredientInput[],
): Promise<RecipeIngredientsResponse> {
  const { data } = await client.put<RecipeIngredientsResponse>(
    `/recipes/${recipeId}/ingredients`,
    { ingredients },
  )
  return data
}
