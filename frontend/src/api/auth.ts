import client from './client'
import type { LoginResponse } from '@/types'

export async function login(email: string, password: string): Promise<LoginResponse> {
  const { data } = await client.post<LoginResponse>('/auth/login', { email, password })
  return data
}

export async function register(params: {
  email: string
  password: string
  full_name: string
  role: string
}): Promise<LoginResponse> {
  const { data } = await client.post<LoginResponse>('/auth/register', params)
  return data
}

export async function refreshToken(): Promise<{ access_token: string; expires_in: number }> {
  const { data } = await client.post('/auth/refresh')
  return data
}

export async function logout(): Promise<void> {
  await client.post('/auth/logout')
}

export interface QRGenerateResponse {
  qr_token: string
  qr_image_base64: string
  expires_at: string
}

export async function generateQR(userId: string): Promise<QRGenerateResponse> {
  const { data } = await client.get<QRGenerateResponse>(`/qr/generate/${userId}`)
  return data
}

export async function validateQR(token: string): Promise<LoginResponse> {
  const { data } = await client.post<LoginResponse>('/qr/validate', { token })
  return data
}
