import React from 'react'
import { Button, Modal, Tag, Typography, Space, Spin, Empty, Collapse } from 'antd'
import {
  FileTextOutlined,
  ApartmentOutlined,
  EditOutlined,
  CodeOutlined,
  BookOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { LearningResource } from '../types'

const { Text } = Typography

type MindmapNode = {
  id: string
  label: string
  children: MindmapNode[]
}

type VideoSlide = {
  start: number
  end: number
  title: string
  bullets: string[]
  caption?: string
  teacher_script?: string
  examples?: string[]
  interaction_question?: string
  core_question?: string
  key_points?: string[]
  case_detail?: string
  misconception?: string
  self_check?: string
  visual?: {
    type?: string
    keywords?: string[]
    items?: Array<string | { label?: string; year?: string; value?: string }>
    steps?: string[]
  }
}

type VideoLikeSlides = {
  mode: 'video_like_slides'
  title: string
  duration_seconds: number
  slides: VideoSlide[]
  production_pack?: VideoProductionPack
}

type VideoProductionPack = {
  pipeline: string
  agents?: Array<{ name: string; output: string }>
  script?: Array<{
    scene: number
    start: number
    end: number
    title: string
    screen_bullets: string[]
    narration: string
    subtitle: string
    visual_instruction: Record<string, unknown>
  }>
  subtitles_srt?: string
  voiceover_segments?: Array<{
    id: string
    text: string
    start: number
    end: number
    suggested_voice: string
    output_file: string
  }>
  voiceover_text?: string
  static_pages?: Array<{
    page_id: string
    title: string
    duration_seconds: number
    html: string
    visual_type: string
    keywords: string[]
  }>
  composition_plan?: {
    canvas?: { width: number; height: number; fps: number }
    timeline?: Array<{ start: number; end: number; page: string; audio: string; subtitle: string }>
    recommended_tools?: string[]
    ffmpeg_outline?: string
  }
}

type VideoShot = {
  id: string
  slide: VideoSlide
  slideIndex: number
  start: number
  end: number
  phase: 'intro' | 'explain' | 'example' | 'recap'
  headline: string
  caption: string
  bullets: string[]
  note: string
  visualKeywords: string[]
}

type LearningCard = {
  question: string
  points: string[]
  caseText: string
  tip: string
  check: string
}

const resourceTypeConfig: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  document: { icon: <FileTextOutlined />, color: 'blue', label: '课程讲义' },
  mindmap: { icon: <ApartmentOutlined />, color: 'purple', label: '思维导图' },
  exercise: { icon: <EditOutlined />, color: 'green', label: '练习题' },
  code: { icon: <CodeOutlined />, color: 'orange', label: '代码案例' },
  reading: { icon: <BookOutlined />, color: 'cyan', label: '拓展阅读' },
  video: { icon: <VideoCameraOutlined />, color: 'red', label: '仿视频微课' },
}

interface ResourceModalProps {
  resource: LearningResource | null
  open: boolean
  loading?: boolean
  onClose: () => void
}

const cleanMindmapLabel = (line: string) => {
  let label = line.trim()
  if (!label || label.startsWith('::')) return ''
  label = label.replace(/^[-*]\s+/, '')
  const rootMatch = label.match(/^root\s*\(\((.*)\)\)$/)
  if (rootMatch) return rootMatch[1].trim()
  const doubleCircleMatch = label.match(/^\(\((.*)\)\)$/)
  if (doubleCircleMatch) return doubleCircleMatch[1].trim()
  const bracketMatch = label.match(/^[[［](.*)[]］]$/)
  if (bracketMatch) return bracketMatch[1].trim()
  return label
}

const parseMindmap = (source: string): MindmapNode | null => {
  const lines = source.replace(/\t/g, '  ').split(/\r?\n/)
  const root: MindmapNode = { id: 'root', label: '思维导图', children: [] }
  const stack: Array<{ indent: number; node: MindmapNode }> = [{ indent: -1, node: root }]
  let count = 0

  for (const rawLine of lines) {
    const trimmed = rawLine.trim()
    if (!trimmed || trimmed === 'mindmap' || trimmed.startsWith('%%')) continue

    const label = cleanMindmapLabel(trimmed)
    if (!label) continue

    const indent = rawLine.match(/^\s*/)?.[0].length || 0
    const node: MindmapNode = { id: `mindmap-${count++}`, label, children: [] }
    while (stack.length > 1 && indent <= stack[stack.length - 1].indent) {
      stack.pop()
    }
    stack[stack.length - 1].node.children.push(node)
    stack.push({ indent, node })
  }

  return root.children[0] || null
}

const extractMermaidSource = (content: string) => {
  const fenced = content.match(/```mermaid\s*([\s\S]*?)```/i)
  if (fenced) return fenced[1].trim()
  const trimmed = content.trim()
  return trimmed.startsWith('mindmap') ? trimmed : ''
}

const parseVideoLikeSlides = (content: string): VideoLikeSlides | null => {
  try {
    const parsed = JSON.parse(content)
    if (parsed?.mode !== 'video_like_slides' || !Array.isArray(parsed.slides)) return null
    return parsed as VideoLikeSlides
  } catch {
    return null
  }
}

const formatTime = (seconds: number) => {
  const safeSeconds = Math.max(0, Math.floor(seconds))
  const minutes = Math.floor(safeSeconds / 60)
  const rest = safeSeconds % 60
  return `${minutes}:${String(rest).padStart(2, '0')}`
}

const MindmapTree: React.FC<{ node: MindmapNode; depth?: number }> = ({ node, depth = 0 }) => {
  const colors = ['#1677ff', '#722ed1', '#13c2c2', '#fa8c16', '#52c41a']
  const color = colors[depth % colors.length]

  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, marginTop: depth === 0 ? 0 : 12 }}>
      <div
        style={{
          minWidth: depth === 0 ? 180 : 150,
          maxWidth: 280,
          padding: depth === 0 ? '14px 16px' : '10px 12px',
          borderRadius: 8,
          border: `1px solid ${color}`,
          background: depth === 0 ? color : 'rgba(255,255,255,0.76)',
          color: depth === 0 ? '#fff' : 'var(--text-primary)',
          fontWeight: depth <= 1 ? 700 : 500,
          lineHeight: 1.5,
          wordBreak: 'break-word',
        }}
      >
        {node.label}
      </div>
      {node.children.length > 0 && (
        <div style={{ borderLeft: '1px solid rgba(72,102,153,0.18)', paddingLeft: 14 }}>
          {node.children.map((child) => (
            <MindmapTree key={child.id} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

const MermaidMindmap: React.FC<{ source: string }> = ({ source }) => {
  const root = React.useMemo(() => parseMindmap(source), [source])
  if (!root) {
    return (
      <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.6 }}>
        {source}
      </pre>
    )
  }

  return (
    <div style={{ overflow: 'auto', padding: 8 }}>
      <MindmapTree node={root} />
    </div>
  )
}

const splitScript = (script?: string, fallback?: string) => {
  const text = (script || fallback || '').replace(/\s+/g, ' ').trim()
  if (!text) return []
  const parts = text.split(/(?<=[。！？!?；;])\s*/)
  return parts.map((part) => part.trim()).filter(Boolean)
}

const normalizeLearningText = (text?: string) => (text || '').replace(/\s+/g, ' ').trim()

const isLowValueLine = (line: string, slide: VideoSlide) => {
  const text = normalizeLearningText(line)
  if (!text) return true
  const compact = text.replace(/[：:，,。！？!?；;"“”'、\s]/g, '')
  const title = normalizeLearningText(slide.title).replace(/[：:，,。！？!?；;"“”'、\s]/g, '')
  const topicBits = [slide.title, ...(slide.visual?.keywords || [])]
    .map((item) => normalizeLearningText(String(item)).replace(/[：:，,。！？!?；;"“”'、\s]/g, ''))
    .filter(Boolean)
  if (compact === title) return true
  if (topicBits.some((item) => item && compact === item)) return true
  return /^(这一页|本页|本镜头|围绕|学习目标|教材案例|核心概念)$/.test(compact) || text.length < 8
}

const buildLearningCard = (slide: VideoSlide, shot: Pick<VideoShot, 'phase' | 'caption' | 'note'>): LearningCard => {
  const scriptLines = splitScript(slide.teacher_script, slide.caption)
  const rawPoints = [
    ...(slide.key_points || []),
    ...(slide.bullets || []),
    ...scriptLines,
  ].map(normalizeLearningText)
  const usefulPoints = rawPoints
    .filter((line, index, arr) => line && !isLowValueLine(line, slide) && arr.indexOf(line) === index)
    .slice(0, 4)
  const examples = (slide.examples || []).map(normalizeLearningText).filter(Boolean)
  const fallbackTopic = normalizeLearningText(slide.title || '本知识点')
  const firstPoint = usefulPoints[0] || normalizeLearningText(shot.caption) || `${fallbackTopic}需要结合具体背景、风险和结论来理解。`

  return {
    question: normalizeLearningText(slide.core_question)
      || (shot.phase === 'recap'
        ? '学完这一页后，你能解释它解决了什么问题吗？'
        : `${fallbackTopic}说明了什么关键问题？`),
    points: usefulPoints.length >= 2
      ? usefulPoints.slice(0, 3)
      : [
        firstPoint,
        examples[0] || `学习时要追问：这个案例的背景是什么、暴露了什么问题、最后得到什么结论。`,
        normalizeLearningText(slide.misconception) || `不要只记住标题，要能说出它和“${fallbackTopic}”之间的关系。`,
      ],
    caseText: normalizeLearningText(slide.case_detail) || examples[0] || firstPoint,
    tip: normalizeLearningText(slide.misconception)
      || `易错提醒：不要把“${fallbackTopic}”当成孤立名词，应结合条件、过程和影响来判断。`,
    check: normalizeLearningText(slide.self_check)
      || normalizeLearningText(slide.interaction_question)
      || `请用 2 句话说明“${fallbackTopic}”的核心结论，并举一个应用场景。`,
  }
}

const buildVideoShots = (lesson: VideoLikeSlides): VideoShot[] => {
  const shots: VideoShot[] = []
  lesson.slides.forEach((slide, slideIndex) => {
    const slideDuration = Math.max(1, slide.end - slide.start)
    const shotCount = slideDuration >= 24 ? 4 : 3
    const phases: VideoShot['phase'][] = shotCount === 4
      ? ['intro', 'explain', 'example', 'recap']
      : ['intro', 'explain', 'recap']
    const scripts = splitScript(slide.teacher_script, slide.caption)
    const keywords = slide.visual?.keywords || slide.visual?.steps || slide.bullets

    phases.forEach((phase, phaseIndex) => {
      const start = Math.round(slide.start + (slideDuration / shotCount) * phaseIndex)
      const end = phaseIndex === phases.length - 1
        ? slide.end
        : Math.round(slide.start + (slideDuration / shotCount) * (phaseIndex + 1))
      const visibleCount = Math.min(slide.bullets.length, Math.max(2, Math.min(3, phaseIndex + 2)))
      const caption = scripts[phaseIndex]
        || scripts[Math.min(scripts.length - 1, Math.max(0, phaseIndex))]
        || slide.caption
        || slide.bullets[Math.min(slide.bullets.length - 1, phaseIndex)]
        || slide.title
      const note = phase === 'intro'
        ? (slide.case_detail || scripts[0] || `先明确“${slide.title}”要解决的问题，再观察案例中的背景、风险和结论。`)
        : phase === 'example'
          ? (slide.case_detail || slide.examples?.[0] || caption)
          : phase === 'recap'
            ? (slide.self_check || slide.interaction_question || '请用自己的话复述这一页的关键结论，并说明一个应用场景。')
            : caption
      const exampleText = slide.examples?.[0]
      const headlineMap: Record<VideoShot['phase'], string> = {
        intro: slide.title,
        explain: slide.bullets[0] || slide.title,
        example: exampleText || slide.bullets[1] || slide.title,
        recap: slide.interaction_question || slide.caption || slide.title,
      }

      shots.push({
        id: `${slideIndex}-${phase}-${phaseIndex}`,
        slide,
        slideIndex,
        start,
        end,
        phase,
        headline: headlineMap[phase],
        caption,
        bullets: slide.bullets.filter((item) => !isLowValueLine(item, slide)).slice(0, visibleCount),
        note,
        visualKeywords: keywords.slice(0, 3).map((item) => String(item)),
      })
    })
  })
  return shots
}

const getShotLabel = (phase: VideoShot['phase']) => {
  const labels: Record<VideoShot['phase'], string> = {
    intro: '镜头引入',
    explain: '重点展开',
    example: '案例演示',
    recap: '总结提问',
  }
  return labels[phase]
}

const VideoVisual: React.FC<{ shot: VideoShot; progress: number }> = ({ shot, progress }) => {
  const slide = shot.slide
  const visual = slide.visual || {}
  const keywords = shot.visualKeywords.length > 0 ? shot.visualKeywords : slide.bullets.slice(0, 3)
  const steps = (visual.steps || keywords).slice(0, 3)
  const visualChipStyle: React.CSSProperties = {
    minWidth: 0,
    maxWidth: 168,
    textAlign: 'center',
    borderRadius: 8,
    padding: '9px 10px',
    background: 'linear-gradient(135deg, rgba(22,119,255,0.34), rgba(99,102,241,0.28))',
    border: '1px solid rgba(174,196,255,0.46)',
    color: '#f8fbff',
    fontWeight: 700,
    lineHeight: 1.35,
    boxShadow: '0 10px 28px rgba(0,0,0,0.20), inset 0 1px 0 rgba(255,255,255,0.14)',
    textShadow: '0 1px 2px rgba(0,0,0,0.55)',
    wordBreak: 'break-word',
    overflowWrap: 'anywhere',
  }
  const pulseStyle: React.CSSProperties = {
    width: 58,
    height: 58,
    borderRadius: 999,
    background: `conic-gradient(from ${Math.round(progress * 360)}deg, #7dd3fc, #818cf8, #34d399, #7dd3fc)`,
    boxShadow: '0 0 34px rgba(125,211,252,0.36)',
  }

  if (visual.type === 'flow') {
    return (
      <div className="video-shot-enter" style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.max(1, steps.length)}, minmax(0, 1fr))`, gap: 10, alignItems: 'center', width: '100%', position: 'relative' }}>
        {steps.map((step, index) => (
          <div key={`${step}-${index}`} style={{ position: 'relative', minWidth: 0 }}>
            <div style={{ ...visualChipStyle, maxWidth: '100%', minHeight: 58, display: 'flex', alignItems: 'center', justifyContent: 'center', animationDelay: `${index * 120}ms` }} className="video-chip-pop">{step}</div>
            {index < steps.length - 1 && (
              <div
                style={{
                  position: 'absolute',
                  right: -8,
                  top: '50%',
                  width: 10,
                  height: 2,
                  background: `linear-gradient(90deg, rgba(125,211,252,${0.25 + progress * 0.55}), rgba(129,140,248,0.72))`,
                  transform: 'translateY(-50%)',
                  borderRadius: 999,
                  pointerEvents: 'none',
                }}
              />
            )}
          </div>
        ))}
      </div>
    )
  }

  if (visual.type === 'timeline') {
    return (
      <div className="video-shot-enter" style={{ width: '100%', display: 'grid', gridTemplateColumns: `repeat(${Math.max(1, keywords.length)}, 1fr)`, gap: 10, alignItems: 'start' }}>
        {keywords.map((keyword, index) => (
          <div key={`${keyword}-${index}`} style={{ display: 'grid', gap: 10, justifyItems: 'center', opacity: progress + 0.25 > index / 3 ? 1 : 0.42 }}>
            <div style={{ width: 14, height: 14, borderRadius: 999, background: index <= Math.floor(progress * 4) ? '#7dd3fc' : 'rgba(255,255,255,0.28)', boxShadow: '0 0 18px rgba(125,211,252,0.35)' }} />
            <div style={{ ...visualChipStyle, minWidth: 0, maxWidth: '100%' }}>{keyword}</div>
          </div>
        ))}
      </div>
    )
  }

  if (visual.type === 'compare') {
    const left = keywords.slice(0, 1)
    const right = keywords.slice(1, 3)
    return (
      <div className="video-shot-enter" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, width: '100%' }}>
        {[left, right].map((group, groupIndex) => (
          <div key={groupIndex} style={{ border: '1px solid rgba(174,196,255,0.28)', borderRadius: 10, padding: 12, background: groupIndex === 0 ? 'rgba(37,99,235,0.22)' : 'rgba(20,184,166,0.18)' }}>
            <Text style={{ color: '#dbeafe', fontWeight: 700 }}>{groupIndex === 0 ? '概念侧' : '应用侧'}</Text>
            <div style={{ marginTop: 10, display: 'grid', gap: 8 }}>
              {group.map((keyword, index) => <div key={`${keyword}-${index}`} style={{ ...visualChipStyle, minWidth: 0, maxWidth: '100%' }}>{keyword}</div>)}
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (visual.type === 'quote') {
    return (
      <div className="video-shot-enter" style={{ borderLeft: '3px solid #a78bfa', paddingLeft: 14, color: '#f8fbff', fontSize: 18, textShadow: '0 1px 2px rgba(0,0,0,0.55)' }}>
        {shot.caption || slide.caption || slide.bullets[0] || slide.title}
      </div>
    )
  }

  if (visual.type === 'quiz') {
    return (
      <div className="video-shot-enter" style={{ border: '1px solid rgba(167,139,250,0.62)', background: 'rgba(31,41,80,0.72)', borderRadius: 8, padding: 16, boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.12)' }}>
        <Text strong style={{ color: '#fff' }}>思考题</Text>
        <div style={{ marginTop: 10, color: '#eef2ff', lineHeight: 1.6 }}>{slide.interaction_question || slide.caption || slide.bullets[0]}</div>
      </div>
    )
  }

  return (
    <div className="video-shot-enter" style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 18, alignItems: 'center', width: '100%' }}>
      <div style={pulseStyle} />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 10, justifyItems: 'center' }}>
        {keywords.slice(0, 3).map((keyword, index) => (
          <div
            key={`${keyword}-${index}`}
            className="video-chip-pop"
            style={{ ...visualChipStyle, animationDelay: `${index * 110}ms` }}
          >
            {keyword}
          </div>
        ))}
      </div>
    </div>
  )
}

const VideoLikeSlidesPlayer: React.FC<{ lesson: VideoLikeSlides }> = ({ lesson }) => {
  const [currentTime, setCurrentTime] = React.useState(0)
  const [playing, setPlaying] = React.useState(false)
  const duration = Math.max(lesson.duration_seconds || 0, ...lesson.slides.map((slide) => slide.end || 0), 1)
  const shots = React.useMemo(() => buildVideoShots(lesson), [lesson])
  const currentSlide = lesson.slides.find((slide) => currentTime >= slide.start && currentTime < slide.end)
    || lesson.slides[lesson.slides.length - 1]
    || { start: 0, end: duration, title: lesson.title, bullets: [] }
  const currentShot = shots.find((shot) => currentTime >= shot.start && currentTime < shot.end)
    || shots[shots.length - 1]
    || {
      id: 'fallback',
      slide: currentSlide,
      slideIndex: 0,
      start: currentSlide.start || 0,
      end: currentSlide.end || duration,
      phase: 'intro' as const,
      headline: currentSlide.title,
      caption: currentSlide.caption || '',
      bullets: currentSlide.bullets || [],
      note: currentSlide.caption || '',
      visualKeywords: currentSlide.bullets || [],
    }
  const examples = currentShot.phase === 'example' ? (currentSlide.examples || []) : []
  const shotDuration = Math.max(1, currentShot.end - currentShot.start)
  const shotProgress = Math.max(0, Math.min(1, (currentTime - currentShot.start) / shotDuration))
  const learningCard = React.useMemo(() => buildLearningCard(currentSlide, currentShot), [currentSlide, currentShot])
  const displayPoints = currentShot.bullets.length > 0 ? currentShot.bullets : learningCard.points

  React.useEffect(() => {
    if (!playing) return undefined
    const timer = window.setInterval(() => {
      setCurrentTime((value) => {
        if (value + 1 >= duration) {
          setPlaying(false)
          return duration
        }
        return value + 1
      })
    }, 1000)
    return () => window.clearInterval(timer)
  }, [playing, duration])

  const seekTo = (time: number) => {
    setCurrentTime(Math.max(0, Math.min(duration, time)))
  }

  return (
    <div>
      <style>
        {`
          @keyframes videoShotEnter {
            from { opacity: 0; transform: translateY(10px) scale(0.985); }
            to { opacity: 1; transform: translateY(0) scale(1); }
          }
          @keyframes videoChipPop {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
          }
          .video-shot-enter { animation: videoShotEnter 360ms ease-out both; }
          .video-chip-pop { animation: videoChipPop 340ms ease-out both; }
        `}
      </style>
      <div
        style={{
          aspectRatio: '16 / 9',
          background: 'linear-gradient(135deg, #070b15, #151827)',
          border: '1px solid rgba(255,255,255,0.12)',
          borderRadius: 8,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          maxHeight: '72vh',
        }}
      >
        <div key={currentShot.id} style={{ flex: 1, minHeight: 0, padding: 28, display: 'grid', gridTemplateRows: 'auto minmax(0, 1fr) auto', gap: 14, overflow: 'hidden' }}>
          <div>
            <Text style={{ color: 'rgba(255,255,255,0.55)' }}>{lesson.title} · {getShotLabel(currentShot.phase)}</Text>
            <h2 className="video-shot-enter" style={{ color: '#fff', margin: '8px 0 0', fontSize: 28 }}>{currentShot.headline}</h2>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1.08fr 0.92fr', gap: 20, alignItems: 'stretch', minHeight: 0, overflow: 'hidden' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, minWidth: 0 }}>
              <div className="video-shot-enter" style={{ border: '1px solid rgba(125,211,252,0.24)', background: 'rgba(14,165,233,0.10)', borderRadius: 8, padding: '9px 12px', color: '#e0f2fe', fontSize: 14, lineHeight: 1.5 }}>
                <Text style={{ color: '#7dd3fc', fontWeight: 800 }}>核心问题：</Text>
                <span>{learningCard.question}</span>
              </div>
              <ul style={{ color: 'rgba(255,255,255,0.92)', fontSize: 15, lineHeight: 1.5, margin: 0, paddingLeft: 22 }}>
                {displayPoints.slice(0, 3).map((bullet, index) => (
                  <li className="video-chip-pop" style={{ animationDelay: `${index * 90}ms` }} key={`${bullet}-${index}`}>
                    {bullet}
                  </li>
                ))}
              </ul>
              {examples.length > 0 && (
                <div className="video-shot-enter" style={{ border: '1px solid rgba(94,234,212,0.28)', background: 'rgba(15,118,110,0.18)', borderRadius: 8, padding: '8px 12px', color: '#dffdf8', fontSize: 13, lineHeight: 1.55 }}>
                  <Text style={{ color: '#99f6e4', fontWeight: 700 }}>案例补充：</Text>
                  <span>{examples.slice(0, 2).join('；')}</span>
                </div>
              )}
              {currentShot.phase === 'example' && learningCard.caseText && examples.length === 0 && (
                <div className="video-shot-enter" style={{ border: '1px solid rgba(94,234,212,0.28)', background: 'rgba(15,118,110,0.18)', borderRadius: 8, padding: '8px 12px', color: '#dffdf8', fontSize: 13, lineHeight: 1.55 }}>
                  <Text style={{ color: '#99f6e4', fontWeight: 700 }}>案例展开：</Text>
                  <span>{learningCard.caseText}</span>
                </div>
              )}
              {currentShot.note && (
                <div className="video-shot-enter" style={{ borderRadius: 8, background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.10)', padding: '10px 12px', color: 'rgba(232,238,255,0.88)', fontSize: 13, lineHeight: 1.58 }}>
                  {currentShot.note}
                </div>
              )}
              {(currentShot.phase === 'recap' || currentShot.phase === 'explain') && (
                <div className="video-shot-enter" style={{ borderRadius: 8, background: currentShot.phase === 'recap' ? 'rgba(124,58,237,0.16)' : 'rgba(250,204,21,0.12)', border: '1px solid rgba(255,255,255,0.12)', padding: '8px 12px', color: currentShot.phase === 'recap' ? '#ede9fe' : '#fef3c7', fontSize: 13, lineHeight: 1.55 }}>
                  <Text style={{ color: currentShot.phase === 'recap' ? '#c4b5fd' : '#fde68a', fontWeight: 700 }}>
                    {currentShot.phase === 'recap' ? '自测问题：' : '易错提醒：'}
                  </Text>
                  <span>{currentShot.phase === 'recap' ? learningCard.check : learningCard.tip}</span>
                </div>
              )}
              {currentSlide.teacher_script && currentShot.phase === 'recap' && (
                <div style={{ color: 'rgba(226,232,255,0.78)', fontSize: 13, lineHeight: 1.5, maxHeight: 84, overflow: 'auto', paddingRight: 4 }}>
                  {currentSlide.teacher_script}
                </div>
              )}
            </div>
            <div style={{ borderRadius: 10, background: 'rgba(6,10,24,0.48)', border: '1px solid rgba(174,196,255,0.20)', padding: 18, display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 160, overflow: 'hidden' }}>
              <VideoVisual shot={currentShot} progress={shotProgress} />
            </div>
          </div>
          <div
            style={{
              minHeight: 40,
              borderRadius: 8,
              background: 'rgba(0,0,0,0.36)',
              color: 'rgba(255,255,255,0.88)',
              padding: '8px 12px',
              lineHeight: 1.45,
              maxHeight: 58,
              overflow: 'auto',
              fontSize: 13,
            }}
          >
            {currentShot.caption || ' '}
          </div>
        </div>
        <div style={{ background: 'rgba(3,7,18,0.82)', padding: '10px 12px', borderTop: '1px solid rgba(255,255,255,0.10)' }}>
          <div
            style={{ height: 6, background: 'rgba(255,255,255,0.18)', borderRadius: 999, cursor: 'pointer' }}
            onClick={(event) => {
              const rect = event.currentTarget.getBoundingClientRect()
              seekTo(((event.clientX - rect.left) / rect.width) * duration)
            }}
          >
            <div style={{ width: `${(currentTime / duration) * 100}%`, height: '100%', borderRadius: 999, background: '#6366f1' }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10 }}>
            <Space>
              <Button size="small" onClick={() => setPlaying((value) => !value)} style={{ fontWeight: 700 }}>
                {playing ? '暂停' : '播放'}
              </Button>
              <Text
                style={{
                  color: '#eef4ff',
                  background: 'rgba(15,23,42,0.88)',
                  border: '1px solid rgba(226,232,240,0.16)',
                  borderRadius: 999,
                  padding: '2px 9px',
                  fontWeight: 700,
                  letterSpacing: 0,
                }}
              >
                {formatTime(currentTime)} / {formatTime(duration)}
              </Text>
            </Space>
            <Text style={{ color: 'rgba(226,232,255,0.76)', fontWeight: 600 }}>仿视频微课</Text>
          </div>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'nowrap', marginTop: 10, overflowX: 'auto', paddingBottom: 4 }}>
        {lesson.slides.map((slide, index) => (
          <Button key={`${slide.title}-${index}`} size="small" onClick={() => seekTo(slide.start)} style={{ flex: '0 0 auto' }}>
            {index + 1}. {slide.title}
          </Button>
        ))}
      </div>
    </div>
  )
}

const preStyle: React.CSSProperties = {
  margin: 0,
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
  maxHeight: 260,
  overflow: 'auto',
  background: 'rgba(246,249,255,0.86)',
  border: '1px solid rgba(72,102,153,0.12)',
  borderRadius: 8,
  padding: 12,
  fontSize: 13,
  lineHeight: 1.6,
}

const VideoProductionPackPanel: React.FC<{ pack?: VideoProductionPack }> = ({ pack }) => {
  if (!pack) return null

  const scriptText = (pack.script || [])
    .map((scene) => [
      `场景 ${scene.scene}｜${formatTime(scene.start)}-${formatTime(scene.end)}｜${scene.title}`,
      `屏幕要点：${(scene.screen_bullets || []).join('；')}`,
      `旁白：${scene.narration}`,
      `字幕：${scene.subtitle}`,
    ].join('\n'))
    .join('\n\n')
  const voiceText = (pack.voiceover_segments || [])
    .map((segment) => `${segment.id}｜${formatTime(segment.start)}-${formatTime(segment.end)}｜${segment.output_file}\n${segment.text}`)
    .join('\n\n')
  const pagesText = (pack.static_pages || [])
    .map((page) => `${page.page_id}｜${page.title}｜${page.duration_seconds}s｜${page.visual_type}\n关键词：${(page.keywords || []).join('、')}`)
    .join('\n\n')
  const compositionText = JSON.stringify(pack.composition_plan || {}, null, 2)

  return (
    <div style={{ marginTop: 14 }}>
      <Collapse
        size="small"
        items={[
          {
            key: 'agents',
            label: '多智能体合成流程',
            children: (
              <Space wrap>
                {(pack.agents || []).map((agent) => (
                  <Tag key={`${agent.name}-${agent.output}`} color="blue">{agent.name} → {agent.output}</Tag>
                ))}
              </Space>
            ),
          },
          {
            key: 'script',
            label: '分镜脚本',
            children: <pre style={preStyle}>{scriptText || '暂无分镜脚本'}</pre>,
          },
          {
            key: 'subtitle',
            label: '字幕 SRT',
            children: <pre style={preStyle}>{pack.subtitles_srt || '暂无字幕'}</pre>,
          },
          {
            key: 'voice',
            label: '语音脚本',
            children: <pre style={preStyle}>{voiceText || pack.voiceover_text || '暂无语音脚本'}</pre>,
          },
          {
            key: 'pages',
            label: '静态页面素材',
            children: <pre style={preStyle}>{pagesText || '暂无静态页面素材'}</pre>,
          },
          {
            key: 'compose',
            label: '视频合成计划',
            children: <pre style={preStyle}>{compositionText}</pre>,
          },
        ]}
      />
    </div>
  )
}

const ResourceModal: React.FC<ResourceModalProps> = ({ resource, open, loading, onClose }) => {
  const config = resource ? resourceTypeConfig[resource.resource_type] : null
  const mermaidSource = resource ? extractMermaidSource(resource.content || '') : ''
  const isMindmapResource = mermaidSource.trimStart().startsWith('mindmap')
  const videoLesson = resource?.resource_type === 'video' ? parseVideoLikeSlides(resource.content || '') : null

  return (
    <Modal
      title={
        resource ? (
          <Space>
            {config?.icon}
            <span>{resource.title}</span>
            {config && <Tag color={config.color}>{config.label}</Tag>}
          </Space>
        ) : (
          '资源详情'
        )
      }
      open={open}
      onCancel={onClose}
      footer={null}
      width={800}
      style={{ top: 32 }}
      destroyOnClose
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: '64px 0' }}>
          <Spin size="large" />
        </div>
      ) : resource ? (
        <div className="resource-modal-content">
          {videoLesson ? (
            <>
              <VideoLikeSlidesPlayer lesson={videoLesson} />
              <VideoProductionPackPanel pack={videoLesson.production_pack} />
            </>
          ) : isMindmapResource ? (
            <div style={{ background: 'rgba(246,249,255,0.86)', padding: 16, borderRadius: 8, overflow: 'auto', border: '1px solid rgba(72,102,153,0.12)' }}>
              <Text type="secondary" style={{ marginBottom: 12, display: 'block' }}>思维导图</Text>
              <MermaidMindmap source={mermaidSource} />
            </div>
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ className, children, ...props }) {
                  const isMermaid = (className || '').toLowerCase().includes('language-mermaid')
                  if (isMermaid) {
                    const source = String(children).trim()
                    const isMindmap = source.trimStart().startsWith('mindmap')
                    return (
                      <div style={{ background: 'rgba(246,249,255,0.86)', padding: 16, borderRadius: 8, overflow: 'auto', border: '1px solid rgba(72,102,153,0.12)' }}>
                        <Text type="secondary" style={{ marginBottom: 12, display: 'block' }}>
                          {isMindmap ? '思维导图' : 'Mermaid 图表'}
                        </Text>
                        {isMindmap ? (
                          <MermaidMindmap source={source} />
                        ) : (
                          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.6 }}>{source}</pre>
                        )}
                      </div>
                    )
                  }
                  return (
                    <code className={className} {...props}>
                      {children}
                    </code>
                  )
                },
              }}
            >
              {resource.content || ''}
            </ReactMarkdown>
          )}
        </div>
      ) : (
        <Empty description="无法加载资源内容" />
      )}
    </Modal>
  )
}

export default ResourceModal
