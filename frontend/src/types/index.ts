/** 用户 */
export interface User {
  id: number
  username: string
  email: string
  display_name: string | null
  avatar_url: string | null
  is_active: boolean
  created_at: string
}

/** 登录响应 */
export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

/** 课程 */
export interface Course {
  id: number
  title: string
  description: string | null
  cover_url: string | null
  seed_course: boolean
  is_active: boolean
  created_at: string
  updated_at: string
  chapters?: Chapter[]
}

/** 章节 */
export interface Chapter {
  id: number
  course_id: number
  title: string
  description: string | null
  sort_order: number
  created_at: string
  updated_at: string
  knowledge_points?: KnowledgePoint[]
}

/** 知识点 */
export interface KnowledgePoint {
  id: number
  chapter_id: number
  title: string
  content: string | null
  difficulty: 'easy' | 'medium' | 'hard'
  prerequisites: number[]
  sort_order: number
  created_at: string
  updated_at: string
}

/** 文档 */
export interface Document {
  id: number
  course_id: number
  title: string
  file_type: string
  file_path: string
  file_size: number
  page_count: number
  status: string
  created_at: string
  updated_at: string
}

/** 学习资源 */
export interface LearningResource {
  id: number
  user_id: number
  course_id: number
  chapter_id: number | null
  knowledge_point_id: number | null
  resource_type: 'document' | 'mindmap' | 'exercise' | 'code' | 'reading' | 'video'
  title: string
  content: string | null
  metadata: Record<string, unknown> | null
  is_generated: boolean
  created_at: string
}

/** 画像 */
export interface StudentProfile {
  id: number
  user_id: number
  profile_data: {
    knowledge_base: Record<string, unknown>
    cognitive_style: Record<string, unknown>
    learning_goals: Record<string, unknown>
    knowledge_gaps: string[]
    learning_pace: Record<string, unknown>
    interest_direction: Record<string, unknown>
    weak_points: string[]
  }
  version: number
  created_at: string
  updated_at: string
}

/** 学习路径 */
export interface StudyPath {
  id: number
  user_id: number
  course_id: number
  path_data: {
    nodes: StudyPathNode[]
    current_index: number
  }
  progress: number
  is_active: boolean
  created_at: string
  updated_at: string
}

/** 路径节点 */
export interface StudyPathNode {
  id: string
  title: string
  type: 'learn' | 'practice' | 'review' | 'exam'
  knowledge_point_id?: number
  status: 'pending' | 'in_progress' | 'completed'
  estimated_minutes: number
  completed_at?: string
}

/** 问答记录 */
export interface QARecord {
  id: number
  user_id: number
  course_id: number | null
  question: string
  answer: string | null
  resource_ids: number[]
  metadata: Record<string, unknown> | null
  created_at: string
}

/** 评估 */
export interface Evaluation {
  id: number
  user_id: number
  course_id: number | null
  scores: Record<string, number>
  suggestions: string[]
  strategy_signals: Record<string, unknown>
  report_data: Record<string, unknown>
  created_at: string
}

/** 系统配置 */
export interface SystemConfig {
  id: number
  config_key: string
  config_value: string
  config_type: string
  description: string | null
  is_secret: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

/** API 通用响应 */
export interface APIResponse<T> {
  code: number
  message: string
  data: T | null
}
