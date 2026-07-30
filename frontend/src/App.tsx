import React, { lazy, Suspense, useEffect } from "react"
import { Routes, Route, Navigate } from "react-router-dom"
import { Spin } from "antd"
import { useAuthStore } from "./store"
import AppLayout from "./components/AppLayout"

const LoginPage = lazy(() => import("./pages/LoginPage"))
const Dashboard = lazy(() => import("./pages/Dashboard"))
const ProfilePage = lazy(() => import("./pages/ProfilePage"))
const LearningPath = lazy(() => import("./pages/LearningPath"))
const ResourcesPage = lazy(() => import("./pages/ResourcesPage"))
const QAPage = lazy(() => import("./pages/QAPage"))
const EvaluationPage = lazy(() => import("./pages/EvaluationPage"))
const AgentPage = lazy(() => import("./pages/AgentPage"))
const CoursesPage = lazy(() => import("./pages/CoursesPage"))
const SettingsPage = lazy(() => import("./pages/SettingsPage"))

const PageLoading = () => (
  <div style={{ minHeight: 240, display: "flex", alignItems: "center", justifyContent: "center" }}>
    <Spin size="large" tip="页面加载中..." />
  </div>
)

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
    <Suspense fallback={<PageLoading />}>
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
          <Route path="courses" element={<CoursesPage />} />
          <Route path="resources" element={<ResourcesPage />} />
          <Route path="path" element={<LearningPath />} />
          <Route path="qa" element={<QAPage />} />
          <Route path="evaluation" element={<EvaluationPage />} />
          <Route path="agent" element={<AgentPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </Suspense>
  )
}

export default App
