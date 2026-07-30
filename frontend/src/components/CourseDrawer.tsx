import React, { useEffect, useState } from 'react'
import { Spin, message } from 'antd'
import {
  DownOutlined,
  RightOutlined,
} from '@ant-design/icons'
import { chapterApi } from '../services/api'
import type { Chapter, KnowledgePoint } from '../types'

interface CourseDrawerProps {
  courseId: number
  open: boolean
  onClose: () => void
  activeChapterId: number | null
  activeKpId: number | null
  onSelectChapter: (chapterId: number) => void
  onSelectKp: (chapterId: number, kpId: number) => void
}

const CourseDrawer: React.FC<CourseDrawerProps> = ({
  courseId,
  open,
  onClose,
  activeChapterId,
  activeKpId,
  onSelectChapter,
  onSelectKp,
}) => {
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [loading, setLoading] = useState(false)
  const [expandedKeys, setExpandedKeys] = useState<string[]>([])

  useEffect(() => {
    if (!open || !courseId) return
    setLoading(true)
    chapterApi.listByCourse(courseId)
      .then((res) => {
        const list = Array.isArray(res.data) ? res.data : []
        setChapters(list)
        // Auto-expand active chapter
        if (activeChapterId) {
          setExpandedKeys((prev) => {
            const key = `chapter-${activeChapterId}`
            return prev.includes(key) ? prev : [...prev, key]
          })
        }
      })
      .catch(() => message.error('章节目录加载失败'))
      .finally(() => setLoading(false))
  }, [open, courseId, activeChapterId])

  if (!open) return null

  return (
    <>
      <button className="catalogue-backdrop" aria-label="关闭目录" onClick={onClose} />
      <aside className="course-catalogue" aria-label="课程目录">
        {loading ? <div className="course-catalogue__loading"><Spin /></div> : chapters.map((chapter, chapterIndex) => {
          const key = `chapter-${chapter.id}`
          const isExpanded = expandedKeys.includes(key)
          const isActiveChapter = chapter.id === activeChapterId
          const knowledgePoints: KnowledgePoint[] = (chapter.knowledge_points || []) as KnowledgePoint[]
          return (
            <section className="catalogue-chapter" key={chapter.id}>
              <div className="catalogue-chapter__row">
                <button className={`catalogue-chapter__title${isActiveChapter ? ' catalogue-chapter__title--active' : ''}`} onClick={() => onSelectChapter(chapter.id)} title={chapter.title}>{`第${chapterIndex + 1}章：${chapter.title}`}</button>
                <button
                  className="catalogue-chapter__toggle"
                  aria-label={`${isExpanded ? '收起' : '展开'}${chapter.title}`}
                  aria-expanded={isExpanded}
                  onClick={() => setExpandedKeys((keys) => isExpanded ? keys.filter((item) => item !== key) : [...keys, key])}
                >
                  {isExpanded ? <DownOutlined /> : <RightOutlined />}
                </button>
              </div>
              {isExpanded && knowledgePoints.length > 0 && (
                <div className="catalogue-chapter__lessons">
                  {knowledgePoints.map((kp, index) => {
                    const isActive = chapter.id === activeChapterId && kp.id === activeKpId
                    return <button key={kp.id} className={`catalogue-lesson${isActive ? ' catalogue-lesson--active' : ''}`} onClick={() => { onSelectKp(chapter.id, kp.id); onClose() }}>{`${chapterIndex + 1}-${index + 1}：${kp.title}`}</button>
                  })}
                </div>
              )}
            </section>
          )
        })}
      </aside>
    </>
  )
}

export default CourseDrawer
