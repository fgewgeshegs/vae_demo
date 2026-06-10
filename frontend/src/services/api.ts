import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import type {
  TokenResponse,
  Course,
  Chapter,
  KnowledgePoint,
  Document,
  LearningResource,
  StudentProfile,
  StudyPath,
  QARecord,
  Evaluation,
  SystemConfig,
  User,
} from '../types'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截器 - 自动附加 token
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('token')
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器 - 统一错误处理
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ========== 认证 API ==========
export const authApi = {
  login: (username: string, password: string) =>
    api.post<TokenResponse>('/auth/login', { username, password }),

  register: (data: { username: string; email: string; password: string; display_name?: string }) =>
    api.post<TokenResponse>('/auth/register', data),

  getMe: () => api.get<User>('/auth/me'),
}

// ========== 课程 API ==========
export const courseApi = {
  list: () => api.get<Course[]>('/courses/'),
  get: (id: number) => api.get<Course>(`/courses/${id}`),
  create: (data: Partial<Course>) => api.post<Course>('/courses/', data),
  delete: (id: number) => api.delete(`/courses/${id}`),
}

// ========== 章节 API ==========
export const chapterApi = {
  listByCourse: (courseId: number) => api.get<Chapter[]>(`/chapters/course/${courseId}`),
  get: (id: number) => api.get<Chapter>(`/chapters/${id}`),
  create: (data: Partial<Chapter>) => api.post<Chapter>('/chapters/', data),
  update: (id: number, data: Partial<Chapter>) => api.put<Chapter>(`/chapters/${id}`, data),
  delete: (id: number) => api.delete(`/chapters/${id}`),
}

// ========== 知识点 API ==========
export const knowledgePointApi = {
  listByChapter: (chapterId: number) =>
    api.get<KnowledgePoint[]>(`/knowledge-points/chapter/${chapterId}`),
  get: (id: number) => api.get<KnowledgePoint>(`/knowledge-points/${id}`),
  create: (data: Partial<KnowledgePoint>) =>
    api.post<KnowledgePoint>('/knowledge-points/', data),
  delete: (id: number) => api.delete(`/knowledge-points/${id}`),
}

// ========== 文档 API ==========
export const documentApi = {
  listByCourse: (courseId: number) => api.get<Document[]>(`/documents/course/${courseId}`),
  get: (id: number) => api.get<Document>(`/documents/${id}`),
  upload: (courseId: number, title: string, file: File) => {
    const formData = new FormData()
    formData.append('course_id', String(courseId))
    formData.append('title', title)
    formData.append('file', file)
    return api.post<Document>('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  delete: (id: number) => api.delete(`/documents/${id}`),
}

// ========== 画像 API ==========
export const profileApi = {
  get: () => api.get<StudentProfile>('/users/profile'),
}

// ========== 资源 API ==========
export const resourceApi = {
  list: (params?: { course_id?: number; resource_type?: string; chapter_id?: number }) =>
    api.get<LearningResource[]>('/resources/', { params }),
  get: (id: number) => api.get<LearningResource>(`/resources/${id}`),
}

// ========== 学习路径 API ==========
export const studyPathApi = {
  list: () => api.get<StudyPath[]>('/study-paths/'),
  get: (id: number) => api.get<StudyPath>(`/study-paths/${id}`),
  update: (id: number, data: Partial<StudyPath>) =>
    api.put<StudyPath>(`/study-paths/${id}`, data),
}

// ========== 问答 API ==========
export const qaApi = {
  list: (courseId?: number) => api.get<QARecord[]>('/qa/', { params: { course_id: courseId } }),
  ask: (question: string, courseId?: number) =>
    api.post<QARecord>('/qa/ask', { question, course_id: courseId }),
  get: (id: number) => api.get<QARecord>(`/qa/${id}`),
}

// ========== 评估 API ==========
export const evaluationApi = {
  list: (courseId?: number) =>
    api.get<Evaluation[]>('/evaluations/', { params: { course_id: courseId } }),
  latest: (courseId?: number) =>
    api.get<Evaluation>('/evaluations/latest', { params: { course_id: courseId } }),
  get: (id: number) => api.get<Evaluation>(`/evaluations/${id}`),
}

// ========== 系统配置 API ==========
export const configApi = {
  list: () => api.get<SystemConfig[]>('/settings/'),
  get: (key: string) => api.get<SystemConfig>(`/settings/${key}`),
  update: (key: string, data: Partial<SystemConfig>) =>
    api.put<SystemConfig>(`/settings/${key}`, data),
}

// ========== 搜索 API ==========
export const searchApi = {
  search: (q: string, courseId?: number) =>
    api.get('/search/', { params: { q, course_id: courseId } }),
}

export default api
