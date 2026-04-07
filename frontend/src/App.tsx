import { Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from '@/components/layout/AppLayout'
import AdminAssignmentsPage from '@/pages/AdminAssignmentsPage'
import AdminDashboardPage from '@/pages/AdminDashboardPage'
import AdminUsersPage from '@/pages/AdminUsersPage'
import DashboardPage from '@/pages/DashboardPage'
import HelpPage from '@/pages/HelpPage'
import LoginPage from '@/pages/LoginPage'
import MenuPage from '@/pages/MenuPage'
import MessagesPage from '@/pages/MessagesPage'
import PantryPage from '@/pages/PantryPage'
import ProfilePage from '@/pages/ProfilePage'
import RecipesPage from '@/pages/RecipesPage'
import ShoppingPage from '@/pages/ShoppingPage'
import TasksPage from '@/pages/TasksPage'
import { useAuthStore } from '@/stores/auth'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((state) => state.user)
  if (user?.role !== 'system_admin') return <Navigate to="/" replace />
  return <>{children}</>
}

function NonAdminRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((state) => state.user)
  if (user?.role === 'system_admin') return <Navigate to="/admin" replace />
  return <>{children}</>
}

function SmartIndex() {
  const user = useAuthStore((state) => state.user)
  if (user?.role === 'system_admin') return <Navigate to="/admin" replace />
  return <DashboardPage />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<SmartIndex />} />
        <Route path="recipes" element={<NonAdminRoute><RecipesPage /></NonAdminRoute>} />
        <Route path="menu" element={<NonAdminRoute><MenuPage /></NonAdminRoute>} />
        <Route path="tasks" element={<NonAdminRoute><TasksPage /></NonAdminRoute>} />
        <Route path="messages" element={<NonAdminRoute><MessagesPage /></NonAdminRoute>} />
        <Route path="shopping" element={<NonAdminRoute><ShoppingPage /></NonAdminRoute>} />
        <Route path="pantry" element={<NonAdminRoute><PantryPage /></NonAdminRoute>} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="help" element={<HelpPage />} />
        <Route path="admin" element={<AdminRoute><AdminDashboardPage /></AdminRoute>} />
        <Route path="admin/users" element={<AdminRoute><AdminUsersPage /></AdminRoute>} />
        <Route path="admin/assignments" element={<AdminRoute><AdminAssignmentsPage /></AdminRoute>} />
      </Route>
    </Routes>
  )
}
