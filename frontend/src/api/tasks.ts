import client from './client'
import type { Task } from '@/types'

export async function getTodayTasks(params?: {
  user_id?: string
  date?: string
}): Promise<Task[]> {
  const { data } = await client.get<Task[]>('/tasks/today', { params })
  return data
}

export async function createTask(task: {
  senior_user_id: string
  title: string
  description?: string
  task_type: string
  priority?: string
  estimated_minutes?: number
  scheduled_date: string
}): Promise<Task> {
  const { data } = await client.post<Task>('/tasks', task)
  return data
}

export async function updateTask(id: string, task: Partial<Task>): Promise<Task> {
  const { data } = await client.put<Task>(`/tasks/${id}`, task)
  return data
}

export async function deleteTask(id: string): Promise<void> {
  await client.delete(`/tasks/${id}`)
}

export async function completeTask(id: string, params: {
  actual_minutes?: number
  notes?: string
  next_notes?: string
}): Promise<void> {
  await client.put(`/tasks/${id}/complete`, params)
}
