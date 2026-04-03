import client from './client'
import type { User } from '@/types'

export async function getProfile(): Promise<User> {
  const { data } = await client.get<User>('/users/me')
  return data
}

export async function updateProfile(updates: {
  full_name?: string
  phone?: string
  address?: string
  emergency_contact?: string
  medical_notes?: string
  care_level?: number
}): Promise<User> {
  const { data } = await client.put<User>('/users/me', updates)
  return data
}
