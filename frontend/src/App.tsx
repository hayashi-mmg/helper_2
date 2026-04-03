import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import LoginPage from '@/pages/LoginPage'
import DashboardPage from '@/pages/DashboardPage'
import RecipesPage from '@/pages/RecipesPage'
import MenuPage from '@/pages/MenuPage'
import TasksPage from '@/pages/TasksPage'
import MessagesPage from '@/pages/MessagesPage'
import ShoppingPage from '@/pages/ShoppingPage'
import PantryPage from '@/pages/PantryPage'
import ProfilePage from '@/pages/ProfilePage'
import AppLayout from '@/components/layout/AppLayout'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
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
        <Route index element={<DashboardPage />} />
        <Route path="recipes" element={<RecipesPage />} />
        <Route path="menu" element={<MenuPage />} />
        <Route path="tasks" element={<TasksPage />} />
        <Route path="messages" element={<MessagesPage />} />
        <Route path="shopping" element={<ShoppingPage />} />
        <Route path="pantry" element={<PantryPage />} />
        <Route path="profile" element={<ProfilePage />} />
      </Route>
    </Routes>
  )
}
