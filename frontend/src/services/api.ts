import axios, { AxiosError, InternalAxiosRequestConfig } from "axios"
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
  LearningTask,
  SystemConfig,
  User,
  ChapterPlan,
  TaskProgress,
  DashboardOverview,
} from "../types"

const api = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
})

// 请求拦截器 - 自动附加 token
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem("token")
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
      localStorage.removeItem("token")
      localStorage.removeItem("user")
      window.location.href = "/login"
    }
    return Promise.reject(error)
  }
)

// ========== 认证 API ==========
export const authApi = {
  login: (username: string, password: string) =>
    api.post<TokenResponse>("/auth/login", { username, password }),

  register: (data: { username: string; email: string; password: string; display_name?: string }) =>
    api.post<TokenResponse>("/auth/register", data),

  getMe: () => api.get<User>("/auth/me"),

  forgotPassword: (email: string) =>
    api.post<{ message: string; dev_code?: string; dev_token?: string }>("/auth/forgot-password", { email }),

  resetPassword: (email: string, code: string, newPassword: string) =>
    api.post<{ message: string }>("/auth/reset-password", { email, code, new_password: newPassword }),
}

// ========== 课程 API ==========
export const courseApi = {
  list: () => api.get<Course[]>("/courses/"),
  get: (id: number) => api.get<Course>(`/courses/${id}`),
  create: (data: Partial<Course>) => api.post<Course>("/courses/", data),
  delete: (id: number) => api.delete(`/courses/${id}`),
}

// ========== 章节 API ==========
export const chapterApi = {
  listByCourse: (courseId: number) => api.get<Chapter[]>(`/chapters/course/${courseId}`),
  get: (id: number) => api.get<Chapter>(`/chapters/${id}`),
  create: (data: Partial<Chapter>) => api.post<Chapter>("/chapters/", data),
  update: (id: number, data: Partial<Chapter>) => api.put<Chapter>(`/chapters/${id}`, data),
  delete: (id: number) => api.delete(`/chapters/${id}`),
}

// ========== 知识点 API ==========
export const knowledgePointApi = {
  listByChapter: (chapterId: number) =>
    api.get<KnowledgePoint[]>(`/knowledge-points/chapter/${chapterId}`),
  get: (id: number) => api.get<KnowledgePoint>(`/knowledge-points/${id}`),
  create: (data: Partial<KnowledgePoint>) =>
    api.post<KnowledgePoint>("/knowledge-points/", data),
  delete: (id: number) => api.delete(`/knowledge-points/${id}`),
}

// ========== 文档 API ==========
export const documentApi = {
  listByCourse: (courseId: number) => api.get<Document[]>(`/documents/course/${courseId}`),
  get: (id: number) => api.get<Document>(`/documents/${id}`),
  upload: (courseId: number, title: string, file: File) => {
    const formData = new FormData()
    formData.append("course_id", String(courseId))
    formData.append("title", title)
    formData.append("file", file)
    return api.post<Document>("/documents/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
  },
  delete: (id: number) => api.delete(`/documents/${id}`),
}

// ========== 画像 API ==========
export const profileApi = {
  get: () => api.get<StudentProfile>("/users/profile"),
  update: (data: Record<string, unknown>) =>
    api.put<StudentProfile>("/users/profile", data),
}

// ========== 资源 API ==========
export const resourceApi = {
  list: (params?: { course_id?: number; resource_type?: string; chapter_id?: number; knowledge_point_id?: number }) =>
    api.get<LearningResource[]>("/resources/", { params }),
  get: (id: number) => api.get<LearningResource>(`/resources/${id}`),
}

// ========== 章节学习计划 API ==========
export const chapterPlanApi = {
    get: (chapterId: number) => api.get<ChapterPlan>(`/chapter-plans/${chapterId}`),
    progress: async (chapterId: number) => {
      const res = await api.get<{ tasks: TaskProgress[] }>(`/chapter-plans/${chapterId}/progress`);
      return { ...res, data: res.data?.tasks ?? [] };
    },
    completeTask: (chapterId: number, taskId: string) =>
      api.post(`/chapter-plans/${chapterId}/tasks/${taskId}/complete`),
  }

// ========== 学习路径 API ==========
export const studyPathApi = {
  list: () => api.get<StudyPath[]>("/study-paths/"),
  get: (id: number) => api.get<StudyPath>(`/study-paths/${id}`),
  update: (id: number, data: Partial<StudyPath>) =>
    api.put<StudyPath>(`/study-paths/${id}`, data),
}

// ========== 问答 API ==========
export const qaApi = {
  list: (courseId?: number) => api.get<QARecord[]>("/qa/", { params: { course_id: courseId } }),
  ask: (question: string, courseId?: number) =>
    api.post<QARecord>("/qa/ask", { question, course_id: courseId }),
  get: (id: number) => api.get<QARecord>(`/qa/${id}`),
  count: () => api.get<{ count: number }>("/qa/count"),
}

// ========== 评估 API ==========
export const evaluationApi = {
  list: (courseId?: number) =>
    api.get<Evaluation[]>("/evaluations/", { params: { course_id: courseId } }),
  latest: (courseId?: number) =>
    api.get<Evaluation>("/evaluations/latest", { params: { course_id: courseId } }),
  get: (id: number) => api.get<Evaluation>(`/evaluations/${id}`),
  generate: (courseId?: number) =>
    api.post("/evaluations/generate", null, { params: { course_id: courseId } }),
}

// ========== 仪表盘 API ==========
export const dashboardApi = {
  overview: () => api.get<DashboardOverview>('/dashboard/overview'),
}

// ========== 系统配置 API ==========
export const configApi = {
  list: () => api.get<SystemConfig[]>("/settings/"),
  get: (key: string) => api.get<SystemConfig>(`/settings/${key}`),
  update: (key: string, data: Partial<SystemConfig>) =>
    api.put<SystemConfig>(`/settings/${key}`, data),
}

// ========== 统一对话 API（经 Coordinator 路由到 PathAgent 等） ==========
export const chatApi = {
  send: (message: string, courseId?: number) =>
    api.post<{ type: string; data: Record<string, unknown>; message: string }>("/chat/", {
      message,
      course_id: courseId,
    }, { timeout: 120000 }),

  /** SSE streaming for global Agent with real-time thinking process */
  agentStream: (message: string, courseId?: number): Promise<Response> => {
    const token = localStorage.getItem("token")
    return fetch("/api/v1/chat/agent_stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message, course_id: courseId }),
    })
  },
}

// ========== 学习任务 API ==========
export const taskApi = {
  create: (
    taskType: LearningTask["task_type"],
    input?: Record<string, unknown>,
    courseId?: number,
  ) =>
    api.post<LearningTask>("/tasks/", {
      task_type: taskType,
      course_id: courseId,
      input: input || {},
    }, { timeout: 120000 }),
  list: () => api.get<LearningTask[]>("/tasks/"),
  get: (id: number) => api.get<LearningTask>(`/tasks/${id}`),
}

// ========== 学习行为 API ==========
export const getTaskErrorMessage = (err: unknown, fallback: string) => {
  const error = err as AxiosError<{ detail?: string }>
  if (error.response?.status === 404) {
    return "学习任务接口未加载，请重启后端服务后再试"
  }
  return error.response?.data?.detail || (err as Error)?.message || fallback
}

export const behaviorApi = {
  record: (actionType: string, targetType?: string, targetId?: number, durationSeconds?: number) =>
    api.post("/behaviors/record", null, {
      params: {
        action_type: actionType,
        target_type: targetType,
        target_id: targetId,
        duration_seconds: durationSeconds || 0,
      },
    }),
  stats: () => api.get("/behaviors/stats"),
  recent: (limit?: number) =>
    api.get("/behaviors/recent", { params: { limit: limit || 20 } }),
}

export default api

// ========== 视频生成 API ==========
export interface VideoTask {
  task_id: string
  status: string
  progress: number
  video_path: string | null
  video_url: string | null
  title: string
  error: string | null
  created_at: string
  completed_at?: string
}

export const videoApi = {
  generate: (
    topic: string,
    knowledgePointTitle?: string,
    chapterTitle?: string,
    content?: string,
    knowledgePointId?: number,
  ) =>
    api.post<{
      task_id: string
      status: string
      message: string
      video_url?: string
    }>(
      "/videos/generate",
      {
        knowledge_point_title: knowledgePointTitle,
        knowledge_point_id: knowledgePointId,
        chapter_title: chapterTitle,
        topic,
        content,
      },
      { timeout: 5000 },
    ),

  status: (taskId: string) => api.get<VideoTask>(`/videos/status/${taskId}`),

  list: () =>
    api.get<{ total: number; completed: number; tasks: VideoTask[] }>(
      "/videos/list",
    ),
}
