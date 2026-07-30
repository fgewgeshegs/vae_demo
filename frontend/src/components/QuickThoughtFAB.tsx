import React, { useEffect, useRef, useState } from 'react'
import { Button, Input, message, Spin } from 'antd'
import { CloseOutlined, SendOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { qaApi } from '../services/api'
import type { QARecord } from '../types'
import './QuickThoughtFAB.css'

const { TextArea } = Input

const QuickThoughtFAB: React.FC = () => {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [records, setRecords] = useState<QARecord[]>([])
  const [fabVisible, setFabVisible] = useState(true)
  const [petRevealed, setPetRevealed] = useState(false)
  const lastScrollY = useRef(0)
  const petHideTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const conversationRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onScroll = () => {
      const currentY = window.scrollY
      setFabVisible(!(currentY > lastScrollY.current && currentY > 200))
      lastScrollY.current = currentY
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => () => {
    if (petHideTimer.current) clearTimeout(petHideTimer.current)
  }, [])

  useEffect(() => {
    conversationRef.current?.scrollTo({ top: conversationRef.current.scrollHeight, behavior: 'smooth' })
  }, [records, loading])

  const revealPet = () => {
    if (petHideTimer.current) clearTimeout(petHideTimer.current)
    setPetRevealed(true)
  }

  const closePanel = () => {
    setOpen(false)
    setPetRevealed(false)
  }

  const hidePet = () => {
    if (open) return
    if (petHideTimer.current) clearTimeout(petHideTimer.current)
    petHideTimer.current = setTimeout(() => setPetRevealed(false), 600)
  }

  const handleSubmit = async () => {
    const question = text.trim()
    if (!question || loading) return

    setText('')
    setLoading(true)
    try {
      const response = await qaApi.ask(question, undefined, { source: 'learning_pet' })
      setRecords((previous) => [...previous, response.data])
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '学习助手暂时无法回答，请稍后重试')
      setText(question)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <button
        type="button"
        className={`quick-thought-trigger ${fabVisible ? '' : 'is-hidden'} ${petRevealed || open ? 'is-revealed' : ''}`}
        onClick={() => { revealPet(); setOpen((value) => !value) }}
        onMouseEnter={revealPet}
        onMouseLeave={hidePet}
        onFocus={revealPet}
        onBlur={hidePet}
        aria-expanded={open}
        aria-controls="quick-thought-panel"
        aria-label={open ? '收起学习小精灵对话' : '打开学习小精灵对话'}
      >
        <span className={`quick-thought-pet ${loading ? 'is-thinking' : records.length > 0 ? 'is-happy' : ''}`} aria-hidden="true">
          <svg viewBox="0 0 160 132" role="presentation">
            <path className="quick-thought-pet__shadow" d="M38 114c16-9 68-9 84 0-16 10-68 10-84 0Z" />
            <path className="quick-thought-pet__cover" d="M20 33c22-12 46-13 60-2v73c-17-10-39-8-58 2L20 33Z" />
            <path className="quick-thought-pet__cover" d="M140 33c-22-12-46-13-60-2v73c17-10 39-8 58 2l2-73Z" />
            <path className="quick-thought-pet__page" d="M30 41c18-8 34-8 47 0v52c-14-7-30-7-46 0l-1-52Z" />
            <path className="quick-thought-pet__page" d="M130 41c-18-8-34-8-47 0v52c14-7 30-7 46 0l1-52Z" />
            <path className="quick-thought-pet__spine" d="M80 31v73" />
            <g className="quick-thought-pet__face"><circle cx="57" cy="65" r="8" /><circle cx="103" cy="65" r="8" /><path d="M72 79c5 5 11 5 16 0" /></g>
            <path className="quick-thought-pet__bookmark" d="M112 39v18l-6-4-6 4V37" />
          </svg>
        </span>
      </button>
      {open && <>
        <button type="button" className="quick-thought-backdrop" aria-label="关闭学习小精灵对话" onClick={closePanel} />
        <section id="quick-thought-panel" className="quick-thought-panel fade-in" aria-label="学习小精灵对话">
          <header className="quick-thought-heading">
            <div><ThunderboltOutlined /> <span>学习小精灵</span></div>
            <button type="button" onClick={closePanel} aria-label="关闭学习助手" title="关闭"><CloseOutlined /></button>
          </header>
          <div ref={conversationRef} className="quick-thought-conversation" aria-live="polite">
            {records.length === 0 && !loading && <p className="quick-thought-welcome">卡在一个概念上？把问题交给我，我们一起拆开它。</p>}
            {records.map((record) => <React.Fragment key={record.id}>
              <div className="quick-thought-message quick-thought-message--user">{record.question}</div>
              <div className="quick-thought-message quick-thought-message--assistant">{record.answer}</div>
            </React.Fragment>)}
            {loading && <div className="quick-thought-thinking"><Spin size="small" /> 正在翻阅知识库...</div>}
          </div>
          <div className="quick-thought-composer">
            <TextArea value={text} onChange={(event) => setText(event.target.value)} placeholder="输入你的学习问题" disabled={loading} autoSize={{ minRows: 2, maxRows: 4 }} className="quick-thought-input" onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void handleSubmit() }
            }} />
            <Button type="primary" shape="circle" icon={<SendOutlined />} aria-label="发送问题" disabled={!text.trim() || loading} loading={loading} onClick={() => void handleSubmit()} />
          </div>
          <p className="quick-thought-hint">Enter 发送，Shift + Enter 换行</p>
        </section>
      </>}
    </>
  )
}

export default QuickThoughtFAB
