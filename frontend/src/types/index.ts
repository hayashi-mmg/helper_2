export interface User {
  id: string
  email: string
  full_name: string
  role: 'senior' | 'helper' | 'care_manager' | 'system_admin'
  phone?: string
  address?: string
  emergency_contact?: string
  medical_notes?: string
  care_level?: number
  is_active: boolean
  last_login_at?: string
  created_at: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: {
    id: string
    email: string
    full_name: string
    role: string
  }
}

export interface Recipe {
  id: string
  name: string
  category: string
  type: string
  difficulty: string
  cooking_time: number
  ingredients?: string
  instructions?: string
  memo?: string
  recipe_url?: string
  created_at: string
  updated_at: string
}

export interface PaginationInfo {
  page: number
  limit: number
  total: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

export interface RecipeListResponse {
  recipes: Recipe[]
  pagination: PaginationInfo
}

export interface Task {
  id: string
  senior_user_id: string
  helper_user_id?: string
  title: string
  description?: string
  task_type: string
  priority: string
  estimated_minutes?: number
  scheduled_date: string
  scheduled_start_time?: string
  scheduled_end_time?: string
  status: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  sender_id: string
  receiver_id: string
  content: string
  message_type: string
  is_read: boolean
  read_at?: string
  created_at: string
}

// --- Menu ---

export interface RecipeBrief {
  id: string
  name: string
  cooking_time: number
}

export interface MenuRecipeEntry {
  recipe_type: string
  recipe: RecipeBrief
}

export interface MealSlotResponse {
  breakfast: MenuRecipeEntry[]
  dinner: MenuRecipeEntry[]
}

export interface MenuSummary {
  total_recipes: number
  avg_cooking_time: number
  category_distribution: Record<string, number>
}

export interface WeeklyMenuResponse {
  week_start: string
  menus: Record<string, MealSlotResponse>
  summary: MenuSummary
}

export interface MenuRecipeRef {
  recipe_id: string
  recipe_type: string
}

export interface MealSlotUpdate {
  breakfast: MenuRecipeRef[]
  dinner: MenuRecipeRef[]
}

// --- Recipe Ingredients ---

export interface RecipeIngredient {
  id: string
  name: string
  quantity?: string
  category: string
  sort_order: number
  created_at: string
}

export interface RecipeIngredientsResponse {
  recipe_id: string
  recipe_name: string
  ingredients: RecipeIngredient[]
}

export interface RecipeIngredientInput {
  name: string
  quantity?: string
  category: string
  sort_order: number
}

// --- Pantry ---

export interface PantryItem {
  id: string
  name: string
  category: string
  is_available: boolean
  updated_at: string
}

export interface PantryListResponse {
  pantry_items: PantryItem[]
  total: number
}

// --- Shopping ---

export interface ShoppingItem {
  id: string
  item_name: string
  category: string
  quantity?: string
  memo?: string
  status: string
  is_excluded?: boolean
  recipe_sources?: string[]
  excluded_reason?: string
  created_at: string
}

export interface ShoppingRequest {
  id: string
  senior_user_id: string
  helper_user_id: string
  request_date: string
  status: string
  notes?: string
  items: ShoppingItem[]
  created_at: string
}

// --- Shopping List Generation ---

export interface GeneratedItem {
  id: string
  item_name: string
  category: string
  quantity?: string
  memo?: string
  status: string
  is_excluded: boolean
  excluded_reason?: string
  recipe_sources: string[]
}

export interface GenerateSummary {
  total_items: number
  excluded_items: number
  active_items: number
}

export interface GenerateFromMenuResponse {
  id: string
  request_date: string
  status: string
  notes?: string
  source_menu_week: string
  items: GeneratedItem[]
  summary: GenerateSummary
  created_at: string
}

// --- Admin Management ---

export interface AdminUser {
  id: string
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
  is_active: boolean
  last_login_at?: string
  created_at: string
  updated_at?: string
}

export interface AdminUserListResponse {
  users: AdminUser[]
  pagination: PaginationInfo
}

export interface AdminUserCreateResponse {
  id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
  temporary_password: string
  created_at: string
  message: string
}

export interface PasswordResetResponse {
  user_id: string
  temporary_password: string
  message: string
  sessions_invalidated: boolean
}

export interface AssignmentUserBrief {
  id: string
  full_name: string
  role: string
}

export interface Assignment {
  id: string
  helper: AssignmentUserBrief
  senior: AssignmentUserBrief
  assigned_by: AssignmentUserBrief
  status: string
  visit_frequency?: string
  preferred_days?: number[]
  preferred_time_start?: string
  preferred_time_end?: string
  notes?: string
  start_date: string
  end_date?: string
  created_at: string
  updated_at?: string
}

export interface AssignmentListResponse {
  assignments: Assignment[]
  pagination: PaginationInfo
}

export interface AuditLog {
  id: string
  user_id?: string
  user_email?: string
  user_role?: string
  action: string
  resource_type: string
  resource_id?: string
  changes?: Record<string, unknown>
  metadata?: Record<string, unknown>
  created_at: string
}

export interface AuditLogListResponse {
  audit_logs: AuditLog[]
  pagination: PaginationInfo
}

export interface DashboardStats {
  total_users: number
  users_by_role: Record<string, number>
  active_users: number
  inactive_users: number
  new_users_this_month: number
  active_assignments: number
  tasks_completed_this_week: number
  login_count_today: number
  generated_at: string
}

export interface Notification {
  id: string
  title: string
  body: string
  notification_type: string
  priority: string
  reference_type?: string
  reference_id?: string
  is_read: boolean
  read_at?: string
  created_at: string
}

export interface NotificationListResponse {
  notifications: Notification[]
  pagination: PaginationInfo
}
