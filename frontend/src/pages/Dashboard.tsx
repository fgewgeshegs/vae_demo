import React, { useCallback, useEffect, useState } from 'react'
import { Alert, Button, Empty, Progress, Skeleton, Tag, Typography } from 'antd'
import {
  ApartmentOutlined, ArrowRightOutlined, BookOutlined, CheckCircleOutlined,
  ClockCircleOutlined, FileSearchOutlined, FolderOpenOutlined, PlayCircleFilled,
  ReloadOutlined, RobotOutlined, RiseOutlined, UserOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { Area, AreaChart, ResponsiveContainer, Tooltip as ChartTooltip, XAxis } from 'recharts'
import { dashboardApi } from '../services/api'
import type { DashboardOverview } from '../types'
import ProfileRadar from '../components/ProfileRadar'
import './Dashboard.css'

const { Text, Title } = Typography

const taskTypeLabel: Record<string, string> = { preview: '预习', learn: '学习', practice: '练习', review: '复习', exam: '测验' }

const shortcuts = [
  { label: '生成学习路径', icon: <ApartmentOutlined />, route: '/path', tone: 'primary' },
  { label: '查看资源', icon: <FolderOpenOutlined />, route: '/resources', tone: 'primary' },
  { label: '生成评估', icon: <RiseOutlined />, route: '/evaluation', tone: 'primary' },
  { label: '开始新对话', icon: <RobotOutlined />, route: '/qa', tone: 'ai' },
  { label: '查看学习画像', icon: <UserOutlined />, route: '/profile', tone: 'primary' },
]

const Dashboard: React.FC = () => {
  const navigate = useNavigate()
  const [overview, setOverview] = useState<DashboardOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pulseMode, setPulseMode] = useState<'today' | 'week'>('today')

  const loadOverview = useCallback(async () => {
    setLoading(true)
    setError(null)
    try { setOverview((await dashboardApi.overview()).data) }
    catch { setOverview(null); setError('学习状态暂时无法加载，请稍后重试。') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { void loadOverview() }, [loadOverview])

  if (loading) return <div className="dashboard-shell"><Skeleton active paragraph={{ rows: 12 }} /></div>
  if (error) return <div className="dashboard-shell dashboard-centered-state"><Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={error}><Button type="primary" icon={<ReloadOutlined />} onClick={() => void loadOverview()}>重新加载</Button></Empty></div>
  if (!overview || overview.status === 'no_path' || !overview.current_task) return <div className="dashboard-shell dashboard-centered-state"><div className="dashboard-empty-icon"><BookOutlined /></div><Title level={3}>先生成一条学习路径</Title><Text type="secondary">建立学习目标后，知境会为你安排下一步该学什么。</Text><Button type="primary" size="large" icon={<ArrowRightOutlined />} onClick={() => navigate('/path')}>去生成学习路径</Button></div>

  const { current_task: task, learning_state: state, recommendation, profile_summary: profileSummary, today_tasks: todayTasks } = overview
  const activity = overview.learning_activity
  const pulseData = pulseMode === 'today'
    ? activity.hourly.filter((item) => item.minutes > 0 || item.hour >= 18).map((item) => ({ ...item, label: `${String(item.hour).padStart(2, '0')}:00` }))
    : activity.daily.map((item) => ({ ...item, label: new Date(`${item.date}T00:00:00`).toLocaleDateString('zh-CN', { weekday: 'short' }) }))
  const stats = [
    { value: `${task.progress_percent}%`, label: '路径完成度' },
    { value: state.completed_nodes, label: '已完成节点' },
    { value: state.recent_qa_count, label: '近期问答' },
    { value: `${task.estimated_minutes || 10}`, label: '本次分钟数' },
  ]

  return <main className="dashboard-shell dashboard-board" aria-label="学习仪表盘">
    {overview.status === 'partial' && <Alert className="dashboard-alert" type="warning" showIcon message="部分学习证据尚未形成，当前建议会在你完成更多学习后持续完善。" />}

    <section className="dashboard-hero-row">
      <div className="dashboard-hero">
        <div><span className="dashboard-kicker">今日学习</span><Title level={2}>现在，完成这一小步</Title><p>{task.course_title} · {taskTypeLabel[task.node_type] || '学习任务'} · 预计 {task.estimated_minutes || 10} 分钟</p></div>
        <div className="dashboard-hero-action"><span>{task.title}</span><Button type="primary" onClick={() => navigate(task.primary_action.target)}>开始学习 <ArrowRightOutlined /></Button></div>
      </div>
      <div className="dashboard-stat-card">{stats.map((stat) => <div className="dashboard-stat" key={stat.label}><strong>{stat.value}</strong><span>{stat.label}</span></div>)}</div>
    </section>

    <section className="dashboard-pulse" aria-label="学习脉冲">
      <div className="dashboard-pulse-heading"><div><span>学习脉冲</span><small>{pulseMode === 'today' ? '按小时查看今天的学习节奏' : '近 7 天的学习投入与完成任务'}</small></div><div className="dashboard-pulse-switch"><button type="button" className={pulseMode === 'today' ? 'is-active' : ''} onClick={() => setPulseMode('today')}>今日</button><button type="button" className={pulseMode === 'week' ? 'is-active' : ''} onClick={() => setPulseMode('week')}>近 7 天</button></div></div>
      <div className="dashboard-pulse-body"><div className="dashboard-pulse-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={pulseData}><defs><linearGradient id="pulseFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#7D6AF8" stopOpacity=".62"/><stop offset="100%" stopColor="#315EF7" stopOpacity="0"/></linearGradient></defs><XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fill: '#AFC1E8', fontSize: 11 }} /><ChartTooltip formatter={(value: number, name: string) => [name === 'minutes' ? `${value} 分钟` : `${value} 项`, name === 'minutes' ? '学习时长' : '完成任务']} labelStyle={{ color: '#172033' }} contentStyle={{ border: 0, borderRadius: 10 }} /><Area type="monotone" dataKey="minutes" stroke="#A99CFF" strokeWidth={3} fill="url(#pulseFill)" /></AreaChart></ResponsiveContainer></div><div className="dashboard-pulse-stats"><div><strong>{activity.week_minutes}</strong><span>本周分钟</span></div><div><strong>{activity.active_days}</strong><span>活跃天数</span></div><div><strong>{pulseMode === 'today' ? activity.hourly.reduce((sum, item) => sum + item.tasks, 0) : activity.daily.reduce((sum, item) => sum + item.tasks, 0)}</strong><span>完成任务</span></div></div></div>
    </section>

    <section className="dashboard-shortcuts" aria-label="快捷学习工具">
      {shortcuts.map((shortcut) => <button type="button" className="dashboard-shortcut" key={shortcut.label} onClick={() => navigate(shortcut.route)}><span className={`dashboard-shortcut-icon is-${shortcut.tone}`}>{shortcut.icon}</span><span>{shortcut.label}</span></button>)}
      <button type="button" className="dashboard-shortcut" onClick={() => void loadOverview()}><span className="dashboard-shortcut-icon is-primary"><ReloadOutlined /></span><span>刷新学习状态</span></button>
    </section>

    <section className="dashboard-core-grid">
      <article className="dashboard-panel dashboard-profile-panel">
        <div className="dashboard-panel-header"><span><UserOutlined /> 学习画像</span><button type="button" onClick={() => navigate('/profile')}>查看详情 <ArrowRightOutlined /></button></div>
        {profileSummary ? <><ProfileRadar profileData={profileSummary.profile_data} size="small" /><div className="dashboard-profile-tags">{[...profileSummary.knowledge_gaps, ...profileSummary.weak_points].slice(0, 3).map((item) => <Tag key={item} color="gold">{item}</Tag>)}</div><Text type="secondary">画像版本 v{profileSummary.version}</Text></> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="继续学习以形成画像" />}
      </article>

      <article className="dashboard-panel dashboard-path-panel">
        <div className="dashboard-panel-header"><span><ApartmentOutlined /> 当前学习路径</span><button type="button" onClick={() => navigate('/path')}>查看全部 <ArrowRightOutlined /></button></div>
        <div className="dashboard-path-title"><span>{taskTypeLabel[task.node_type] || '学习'}</span><strong>{task.title}</strong></div>
        <Progress percent={task.progress_percent} strokeColor="#3D73FF" trailColor="#E7ECF8" showInfo={false} />
        <div className="dashboard-path-meta"><span>{state.completed_nodes} / {state.total_nodes} 个节点已完成</span><span>下一步：{task.next_step || '完成本路径复盘'}</span></div>
        {recommendation?.reasons?.slice(0, 2).map((reason) => <div className="dashboard-evidence" key={reason.evidence}><FileSearchOutlined /><span>{reason.evidence}</span></div>)}
        <Button type="link" onClick={() => navigate('/path')}>继续当前路径 <ArrowRightOutlined /></Button>
      </article>

      <article className="dashboard-panel dashboard-tasks-panel">
        <div className="dashboard-panel-header"><span><CheckCircleOutlined /> 今日待办</span><Tag color="gold">{todayTasks.length} 项</Tag></div>
        <div className="dashboard-tasks-list">{todayTasks.map((item) => <button type="button" className="dashboard-todo" key={item.id} onClick={() => navigate('/path')}><span className={`dashboard-todo-status ${item.status === 'in_progress' ? 'is-current' : ''}`}>{item.status === 'in_progress' ? '进行中' : '待开始'}</span><span><strong>{item.title}</strong><small>{taskTypeLabel[item.node_type] || '学习任务'} · 约 {item.estimated_minutes || 10} 分钟</small></span></button>)}</div>
      </article>
    </section>
  </main>
}

export default Dashboard
