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
