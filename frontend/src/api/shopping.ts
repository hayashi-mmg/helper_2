import client from './client'
import type { ShoppingRequest, ShoppingItem, GenerateFromMenuResponse } from '@/types'

export async function getShoppingRequests(status?: string): Promise<ShoppingRequest[]> {
  const { data } = await client.get<ShoppingRequest[]>('/shopping/requests', {
    params: status ? { status } : undefined,
  })
  return data
}

export async function createShoppingRequest(params: {
  senior_user_id: string
  request_date: string
  notes?: string
  items: { item_name: string; category?: string; quantity?: string; memo?: string }[]
}): Promise<ShoppingRequest> {
  const { data } = await client.post<ShoppingRequest>('/shopping/requests', params)
  return data
}

export async function updateShoppingItem(
  itemId: string,
  updates: { status?: string; memo?: string },
): Promise<ShoppingItem> {
  const { data } = await client.put<ShoppingItem>(`/shopping/items/${itemId}`, updates)
  return data
}

export async function generateFromMenu(params: {
  week_start: string
  notes?: string
}): Promise<GenerateFromMenuResponse> {
  const { data } = await client.post<GenerateFromMenuResponse>(
    '/shopping/requests/generate-from-menu',
    params,
  )
  return data
}

export async function toggleExclude(
  itemId: string,
  isExcluded: boolean,
): Promise<{ id: string; item_name: string; is_excluded: boolean; status: string }> {
  const { data } = await client.put(`/shopping/items/${itemId}/exclude`, {
    is_excluded: isExcluded,
  })
  return data
}
