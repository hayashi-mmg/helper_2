import client from './client'
import type { Recipe, RecipeListResponse } from '@/types'

export async function getRecipes(params?: {
  category?: string
  type?: string
  difficulty?: string
  search?: string
  page?: number
  limit?: number
}): Promise<RecipeListResponse> {
  const { data } = await client.get<RecipeListResponse>('/recipes', { params })
  return data
}

export async function getRecipe(id: string): Promise<Recipe> {
  const { data } = await client.get<Recipe>(`/recipes/${id}`)
  return data
}

export async function createRecipe(recipe: Omit<Recipe, 'id' | 'created_at' | 'updated_at'>): Promise<Recipe> {
  const { data } = await client.post<Recipe>('/recipes', recipe)
  return data
}

export async function updateRecipe(id: string, recipe: Partial<Recipe>): Promise<Recipe> {
  const { data } = await client.put<Recipe>(`/recipes/${id}`, recipe)
  return data
}

export async function deleteRecipe(id: string): Promise<void> {
  await client.delete(`/recipes/${id}`)
}
