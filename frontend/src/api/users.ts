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

export async function changePassword(current_password: string, new_password: string): Promise<{ message: string }> {
  const { data } = await client.put<{ message: string }>('/users/me/password', { current_password, new_password })
  return data
}
