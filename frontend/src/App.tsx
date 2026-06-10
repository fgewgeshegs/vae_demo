import React, { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store'
import AppLayout from './components/AppLayout'
import LoginPage from './pages/LoginPage'
import Dashboard from './pages/Dashboard'
import ProfilePage from './pages/ProfilePage'
import LearningPath from './pages/LearningPath'
import ResourcesPage from './pages/ResourcesPage'
import QAPage from './pages/QAPage'
import EvaluationPage from './pages/EvaluationPage'
import CourseManagement from './pages/CourseManagement'
import SearchPage from './pages/SearchPage'
import SettingsPage from './pages/SettingsPage'

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isLoggedIn = useAuthStore((s) => s.isLoggedIn)
  if (!isLoggedIn) return <Navigate to="/login" replace />
  return <>{children}</>
}

const App: React.FC = () => {
  const loadFromStorage = useAuthStore((s) => s.loadFromStorage)

  useEffect(() => {
    loadFromStorage()
  }, [loadFromStorage])

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
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="path" element={<LearningPath />} />
        <Route path="resources" element={<ResourcesPage />} />
        <Route path="qa" element={<QAPage />} />
        <Route path="evaluation" element={<EvaluationPage />} />
        <Route path="courses" element={<CourseManagement />} />
        <Route path="search" element={<SearchPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}

export default App
