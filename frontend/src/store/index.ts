import { create } from 'zustand'
import type { User, Course } from '../types'

/** 认证状态 */
interface AuthState {
  token: string | null
  user: User | null
  isLoggedIn: boolean
  setAuth: (token: string, user: User) => void
  logout: () => void
  loadFromStorage: () => void
}

const storedAuth = (() => {
  const token = localStorage.getItem('token')
  const userStr = localStorage.getItem('user')
  if (!token || !userStr) return { token: null, user: null, isLoggedIn: false }
  try {
    return { token, user: JSON.parse(userStr) as User, isLoggedIn: true }
  } catch {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    return { token: null, user: null, isLoggedIn: false }
  }
})()

export const useAuthStore = create<AuthState>((set) => ({
  ...storedAuth,

  setAuth: (token, user) => {
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(user))
    set({ token, user, isLoggedIn: true })
  },

  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    set({ token: null, user: null, isLoggedIn: false })
  },

  loadFromStorage: () => {
    const token = localStorage.getItem('token')
    const userStr = localStorage.getItem('user')
    if (token && userStr) {
      try {
        const user = JSON.parse(userStr) as User
        set({ token, user, isLoggedIn: true })
      } catch {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
      }
    }
  },
}))

/** 课程状态 */
interface CourseState {
  courses: Course[]
  currentCourse: Course | null
  loading: boolean
  setCourses: (courses: Course[]) => void
  setCurrentCourse: (course: Course | null) => void
  setLoading: (loading: boolean) => void
}

export const useCourseStore = create<CourseState>((set) => ({
  courses: [],
  currentCourse: null,
  loading: false,
  setCourses: (courses) => set({ courses }),
  setCurrentCourse: (course) => set({ currentCourse: course }),
  setLoading: (loading) => set({ loading }),
}))

/** 全局 UI 状态 */
interface UIState {
  sidebarCollapsed: boolean
  toggleSidebar: () => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
}))
