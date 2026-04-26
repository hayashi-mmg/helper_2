import type {
  AdminUser,
  AdminUserCreateResponse,
  AdminUserListResponse,
  Assignment,
  AssignmentListResponse,
  AuditLogListResponse,
  DashboardStats,
  NotificationListResponse,
  PasswordResetResponse,
} from '@/types'
import client from './client'

// ---------------------------------------------------------------------------
// ユーザー管理
// ---------------------------------------------------------------------------
export async function getAdminUsers(params?: {
  role?: string
  is_active?: boolean
  search?: string
  page?: number
  limit?: number
  sort_by?: string
  sort_order?: string
}): Promise<AdminUserListResponse> {
  const { data } = await client.get<AdminUserListResponse>('/admin/users', { params })
  return data
}

export async function getAdminUser(userId: string): Promise<AdminUser> {
  const { data } = await client.get<AdminUser>(`/admin/users/${userId}`)
  return data
}

export async function createAdminUser(user: {
  email: string
  full_name: string
  role: string
  phone?: string
  address?: string
  emergency_contact?: string
  medical_notes?: string
  care_level?: number
  certification_number?: string
  specialization?: string[]
}): Promise<AdminUserCreateResponse> {
  const { data } = await client.post<AdminUserCreateResponse>('/admin/users', user)
  return data
}

export async function updateAdminUser(
  userId: string,
  updates: Record<string, unknown>,
): Promise<AdminUser> {
  const { data } = await client.put<AdminUser>(`/admin/users/${userId}`, updates)
  return data
}

export async function deactivateUser(userId: string): Promise<AdminUser> {
  const { data } = await client.put<AdminUser>(`/admin/users/${userId}/deactivate`)
  return data
}

export async function activateUser(userId: string): Promise<AdminUser> {
  const { data } = await client.put<AdminUser>(`/admin/users/${userId}/activate`)
  return data
}

export async function resetPassword(userId: string): Promise<PasswordResetResponse> {
  const { data } = await client.post<PasswordResetResponse>(`/admin/users/${userId}/reset-password`)
  return data
}

export async function setUserPassword(userId: string, new_password: string): Promise<{ user_id: string; message: string }> {
  const { data } = await client.put<{ user_id: string; message: string }>(`/admin/users/${userId}/set-password`, { new_password })
  return data
}

// ---------------------------------------------------------------------------
// アサイン管理
// ---------------------------------------------------------------------------
export async function getAssignments(params?: {
  helper_id?: string
  senior_id?: string
  status?: string
  page?: number
  limit?: number
}): Promise<AssignmentListResponse> {
  const { data } = await client.get<AssignmentListResponse>('/admin/assignments', { params })
  return data
}

export async function createAssignment(assignment: {
  helper_id: string
  senior_id: string
  visit_frequency?: string
  preferred_days?: number[]
  preferred_time_start?: string
  preferred_time_end?: string
  start_date?: string
  end_date?: string
  notes?: string
}): Promise<Assignment> {
  const { data } = await client.post<Assignment>('/admin/assignments', assignment)
  return data
}

export async function updateAssignment(
  id: string,
  updates: Record<string, unknown>,
): Promise<Assignment> {
  const { data } = await client.put<Assignment>(`/admin/assignments/${id}`, updates)
  return data
}

export async function deleteAssignment(id: string): Promise<void> {
  await client.delete(`/admin/assignments/${id}`)
}

// ---------------------------------------------------------------------------
// 監査ログ
// ---------------------------------------------------------------------------
export async function getAuditLogs(params?: {
  action?: string
  resource_type?: string
  page?: number
  limit?: number
}): Promise<AuditLogListResponse> {
  const { data } = await client.get<AuditLogListResponse>('/admin/audit-logs', { params })
  return data
}

// ---------------------------------------------------------------------------
// ダッシュボード
// ---------------------------------------------------------------------------
export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await client.get<DashboardStats>('/admin/dashboard/stats')
  return data
}

// ---------------------------------------------------------------------------
// 通知
// ---------------------------------------------------------------------------
export async function getNotifications(params?: {
  is_read?: boolean
  page?: number
  limit?: number
}): Promise<NotificationListResponse> {
  const { data } = await client.get<NotificationListResponse>('/notifications', { params })
  return data
}

export async function markNotificationRead(id: string): Promise<void> {
  await client.put(`/notifications/${id}/read`)
}

export async function markAllNotificationsRead(): Promise<void> {
  await client.put('/notifications/read-all')
}

export async function broadcastNotification(payload: {
  title: string
  body: string
  notification_type?: string
  priority?: string
  target_roles?: string[]
}): Promise<{ message: string; count: number }> {
  const { data } = await client.post<{ message: string; count: number }>('/admin/notifications/broadcast', payload)
  return data
}

// ---------------------------------------------------------------------------
// 献立インポート
// ---------------------------------------------------------------------------
export type ImportRecipeInput = {
  name: string
  category: string
  type: '主菜' | '副菜' | '汁物' | 'ご飯' | 'その他'
  difficulty: string
  cooking_time: number
  ingredients_text?: string | null
  instructions?: string | null
  memo?: string | null
  recipe_url?: string | null
}

export type ImportMenuRecipeRef = {
  recipe_name: string
  recipe_type: '主菜' | '副菜' | '汁物' | 'ご飯' | 'その他'
}

export type ImportMenuSlot = {
  breakfast: ImportMenuRecipeRef[]
  dinner: ImportMenuRecipeRef[]
}

export type MenuImportRequest = {
  target_user_id?: string
  target_user_email?: string
  week_start: string  // YYYY-MM-DD
  recipes: ImportRecipeInput[]
  menu: Record<string, ImportMenuSlot>
  generate_shopping_list?: boolean
  helper_user_id?: string
  dry_run?: boolean
}

export type ShoppingListResult = {
  request_id: string
  total_items: number
  excluded_items: number
  active_items: number
  replaced_existing: boolean
}

export type MenuImportResponse = {
  applied: boolean
  target_user: {
    id: string
    email: string
    full_name: string
    role: string
  }
  week_start: string
  created_recipe_count: number
  reused_recipe_count: number
  replaced_menu: boolean
  shopping_list: ShoppingListResult | null
  warnings: string[]
}

export async function importMenu(payload: MenuImportRequest): Promise<MenuImportResponse> {
  const { data } = await client.post<MenuImportResponse>('/admin/menus/import', payload)
  return data
}
