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
  recommendation_rank?: number
  recommendation_reason?: string
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
    learning_habits?: Record<string, unknown>
    motivation_factors?: Record<string, unknown>
    _meta?: Record<string, unknown>
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
    course_title?: string
    description?: string
    estimated_total_minutes?: number
    strategies_applied?: string[]
    student_state_snapshot_id?: string
    profile_version?: number
    planning_basis?: { level?: string; preference?: string; knowledge_gaps?: string[]; latest_evaluation_id?: number }
    adjustment_summary?: string
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
  type: 'preview' | 'learn' | 'practice' | 'review' | 'exam'
  chapter_id?: number | null
  knowledge_point_id?: number
  chapter_title?: string | null
  knowledge_point_title?: string | null
  resource_ids?: number[]
  learning_content?: string | null
  difficulty?: string | null
  status: 'pending' | 'in_progress' | 'completed'
  estimated_minutes: number
  completed_at?: string
  recommended_resource_types?: string[]
  personalization_reason?: string[]
  state_snapshot_id?: string
}

/** 问答记录 */
export interface QARecord {
  id: number
  user_id: number
  course_id: number | null
  question: string
  answer: string | null
  conversation_id: string | null
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

/** 仪表盘聚合状态 */
export interface DashboardOverview {
  status: 'ready' | 'no_path' | 'no_profile' | 'partial'
  generated_at: string
  current_task: {
    path_id: number
    course_id: number
    course_title: string
    node_id: string
    title: string
    node_type: 'preview' | 'learn' | 'practice' | 'review' | 'exam'
    difficulty: string | null
    estimated_minutes: number
    progress_percent: number
    resource_ids: number[]
    primary_action: { label: string; target: '/path' }
    next_step: string | null
  } | null
  recommendation: {
    headline: string
    reasons: Array<{
      kind: 'knowledge_gap' | 'weak_point' | 'evaluation_signal' | 'learning_pace'
      label: string
      evidence: string
    }>
    profile_version: number | null
  } | null
  learning_state: {
    completed_nodes: number
    total_nodes: number
    recent_qa_count: number
    last_activity_at: string | null
  }
  feedback: {
    message: string
    source: 'evaluation' | 'path_progress' | 'profile'
    strategy_signal: string | null
  } | null
  profile_summary: {
    version: number
    profile_data: StudentProfile['profile_data']
    knowledge_gaps: string[]
    weak_points: string[]
  } | null
  today_tasks: Array<{
    id: string
    title: string
    node_type: 'preview' | 'learn' | 'practice' | 'review' | 'exam' | string
    estimated_minutes: number
    status: 'pending' | 'in_progress' | string
  }>
  learning_activity: {
    daily: Array<{ date: string; minutes: number; tasks: number }>
    hourly: Array<{ hour: number; minutes: number; tasks: number }>
    week_minutes: number
    active_days: number
  }
}

/** 学习任务 */
export interface LearningTaskStep {
  name: string
  status: 'pending' | 'running' | 'done' | 'failed' | 'skipped' | string
  label?: string | null
  error?: string | null
}

export interface AgentResult {
  agent: string
  status: 'success' | 'failed' | string
  type: string
  data: Record<string, unknown>
  state_updates: Record<string, unknown>[]
  artifacts: Record<string, unknown>[]
  next_actions: Record<string, unknown>[]
  errors: Record<string, unknown>[]
  message?: string
}

export interface LearningTask {
  id: number
  task_type: 'generate_study_path' | 'update_profile' | 'generate_learning_resource' | 'pre_generate_course_resources' | 'generate_evaluation'
  user_id: number
  course_id: number | null
  status: 'running' | 'succeeded' | 'failed' | string
  input: Record<string, unknown>
  steps: LearningTaskStep[]
  result: Record<string, unknown> & { agents?: AgentResult[]; message?: string }
  error: string | null
  created_at: string
  updated_at: string
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

/** 章节学习计划 */
export interface ChapterPlan {
  chapter_id: number
  tasks: ChapterTask[]
  estimated_total_minutes: number
  description: string
}

/** 学习计划任务项 */
export interface ChapterTask {
  task_id: string
  task_type: string
  title: string
  description: string
  estimated_minutes: number
  resource_types: string[]
  difficulty: string
}

/** 任务进度 */
export interface TaskProgress {
  task_id: string
  status: string
  correct_rate?: number
  score?: number
}

/** Deterministic five-stage chapter learning loop. */
export interface LearningRunStage {
  stage: 'learn' | 'practice' | 'assess' | 'feedback' | 'review' | 'remedial'
  status: 'locked' | 'available' | 'active' | 'completed'
  evidence: Record<string, unknown>
  started_at: string | null
  completed_at: string | null
}

export interface LearningRun {
  id: number
  chapter_id: number
  status: 'locked' | 'active' | 'completed'
  current_stage: 'locked' | LearningRunStage['stage']
  plan_version: number
  personalization_snapshot: Record<string, unknown>
  lock_reason: { reason_code?: string; blocked_by?: number[]; unlock_condition?: string } | null
  stages: LearningRunStage[]
  started_at: string | null
  completed_at: string | null
}

export interface LearningFeedback {
  assessment_attempt_id: number
  result: 'partial_mastery' | 'mastered'
  mastered: Array<{ knowledge_point_id: number; mastery: number }>
  weak: Array<{ knowledge_point_id: number; mastery: number }>
  next_action: { type: 'review' | 'remedial'; reason: string }
}
