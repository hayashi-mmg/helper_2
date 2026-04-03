import client from './client'
import type { PantryListResponse } from '@/types'

export async function getPantryItems(availableOnly?: boolean): Promise<PantryListResponse> {
  const { data } = await client.get<PantryListResponse>('/pantry', {
    params: availableOnly ? { available_only: true } : undefined,
  })
  return data
}

export async function updatePantryItems(
  items: { name: string; category: string; is_available: boolean }[],
): Promise<PantryListResponse> {
  const { data } = await client.put<PantryListResponse>('/pantry', { items })
  return data
}

export async function deletePantryItem(itemId: string): Promise<void> {
  await client.delete(`/pantry/${itemId}`)
}
