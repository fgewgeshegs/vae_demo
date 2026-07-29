import React, { useEffect, useRef, useState } from 'react'
import { Button, Input, message, Spin } from 'antd'
import { MessageOutlined, RobotOutlined, SendOutlined } from '@ant-design/icons'
import { chatApi } from '../services/api'
import './QuickThoughtFAB.css'

const { TextArea } = Input

const QuickThoughtFAB: React.FC = () => {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [fabVisible, setFabVisible] = useState(true)
  const lastScrollY = useRef(0)

  useEffect(() => {
    const onScroll = () => {
      const sy = window.scrollY
      setFabVisible(!(sy > lastScrollY.current && sy > 200))
      lastScrollY.current = sy
    }
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  const handleSubmit = async () => {
    if (!text.trim()) return
    setLoading(true)
    try {
      const res = await chatApi.send(text.trim())
      message.success({
        icon: <RobotOutlined style={{ color: '#2563eb' }} />,
        content: res.data.message || 'Agent 已完成任务',
        duration: 6,
      })
      setText('')
      setOpen(false)
    } catch (err: any) {
      message.error(err?.response?.data?.detail || 'Agent 处理失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <button
        type="button"
        className={`quick-thought-trigger ${fabVisible ? '' : 'is-hidden'}`}
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-controls="quick-thought-panel"
      >
        <MessageOutlined aria-hidden="true" />
        <span>{open ? '收起对话' : '新建对话'}</span>
      </button>
      {open && (
        <>
          <button type="button" className="quick-thought-backdrop" aria-label="关闭新建对话面板" onClick={() => setOpen(false)} />
          <section id="quick-thought-panel" className="quick-thought-panel fade-in" aria-label="新建学习对话">
            <div className="quick-thought-heading">
              <RobotOutlined style={{ marginRight: 6 }} />
              全局学习 Agent
            </div>
            <TextArea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder='例如：更新我的画像、生成学习路径、评估我的学习...'
              disabled={loading}
              autoSize={{ minRows: 2, maxRows: 5 }}
              className="quick-thought-input"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSubmit()
                }
              }}
            />
            <div className="quick-thought-actions">
              {loading && <span className="quick-thought-status"><Spin size="small" /> 正在处理…</span>}
              <Button type="primary" icon={!loading && <SendOutlined />} disabled={!text.trim() || loading} loading={loading} onClick={() => void handleSubmit()}>
                发送给 Agent
              </Button>
            </div>
            <p className="quick-thought-hint">Enter 发送，Shift + Enter 换行</p>
          </section>
        </>
      )}
    </>
  )
}

export default QuickThoughtFAB
