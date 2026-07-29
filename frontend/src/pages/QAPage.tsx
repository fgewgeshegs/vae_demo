import React, { useEffect, useRef, useState } from 'react'
import { Avatar, Button, Empty, Input, List, Spin, Tag, Typography, message } from 'antd'
import { BookOutlined, CopyOutlined, EditOutlined, FileTextOutlined, MenuFoldOutlined, MenuUnfoldOutlined, PlusOutlined, RobotOutlined, SearchOutlined, SendOutlined, UserOutlined } from '@ant-design/icons'
import { qaApi } from '../services/api'
import type { QARecord } from '../types'
import './QAPage.css'

const { Text } = Typography
const { TextArea } = Input

const QAPage: React.FC = () => {
  const [records, setRecords] = useState<QARecord[]>([])
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [question, setQuestion] = useState('')
  const [mode, setMode] = useState<'quick' | 'expert'>('quick')
  const [historyQuery, setHistoryQuery] = useState('')
  const [historyCollapsed, setHistoryCollapsed] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const loadRecords = async () => {
    setLoading(true)
    try {
      const res = await qaApi.list()
      setRecords(res.data.reverse())
    } catch {
      message.error('问答历史加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadRecords() }, [])
  useEffect(() => { listRef.current?.scrollTo({ top: listRef.current.scrollHeight }) }, [records, selectedConversationId])

  const handleSend = async () => {
    if (!question.trim() || sending) return
    setSending(true)
    try {
      const res = await qaApi.ask(question.trim(), undefined, { mode }, selectedConversationId || undefined)
      const nextConversationId = res.data.conversation_id || `legacy-${res.data.id}`
      setRecords((prev) => [
        ...prev.map((record) => getConversationId(record) === selectedConversationId
          ? { ...record, conversation_id: nextConversationId }
          : record),
        res.data,
      ])
      setSelectedConversationId(nextConversationId)
      setQuestion('')
    } catch {
      message.error('发送失败，请稍后重试')
    } finally {
      setSending(false)
    }
  }

  const getConversationId = (record: QARecord) => record.conversation_id || `legacy-${record.id}`
  const visibleRecords = selectedConversationId
    ? records.filter((record) => getConversationId(record) === selectedConversationId)
    : []
  const matchedRecords = historyQuery.trim()
    ? records.filter((record) => `${record.question} ${record.answer || ''}`.toLowerCase().includes(historyQuery.trim().toLowerCase()))
    : records
  const historyConversations = Array.from(
    matchedRecords.reduce((conversations, record) => {
      const conversationId = getConversationId(record)
      if (!conversations.has(conversationId)) conversations.set(conversationId, record)
      return conversations
    }, new Map<string, QARecord>()).values(),
  )
  const startNewChat = () => {
    setSelectedConversationId(null)
    setQuestion('')
  }
  const closeHistorySearch = () => {
    setSearchOpen(false)
    setHistoryQuery('')
  }

  const copyQuestion = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value)
      message.success('已复制问题')
    } catch {
      message.warning('当前环境无法复制，请手动选择文本')
    }
  }

  if (loading) return <div className="qa-loading"><Spin size="large" /></div>

  return (
    <main className={`qa-agent ${historyCollapsed ? 'qa-agent--history-collapsed' : ''}`} aria-label="智能学习助手">
      <aside className="qa-history" aria-label="问答历史">
        <div className="qa-history__brand"><span><RobotOutlined /><i>学习助手</i></span><span><button type="button" onClick={() => setSearchOpen(true)} title="搜索历史"><SearchOutlined /></button><button type="button" onClick={() => setHistoryCollapsed(true)} title="折叠问答历史"><MenuFoldOutlined /></button></span></div>
        <Button className="qa-new-chat" icon={<PlusOutlined />} onClick={startNewChat}>开启新对话</Button>
        <div className="qa-history__label">最近问答</div>
        <div className="qa-history__list">
          {historyConversations.length === 0 ? <Text type="secondary" className="qa-history__empty">没有匹配的消息</Text> : historyConversations.slice().reverse().map((record) => (
            <button type="button" className={`qa-history__item ${selectedConversationId === getConversationId(record) ? 'is-active' : ''}`} key={getConversationId(record)} onClick={() => setSelectedConversationId(getConversationId(record))}>
              {record.question}
            </button>
          ))}
        </div>
      </aside>
      {historyCollapsed && <button type="button" className="qa-history-expand" onClick={() => setHistoryCollapsed(false)} title="展开问答历史"><MenuUnfoldOutlined /></button>}

      <section className="qa-chat">
        {visibleRecords.length === 0 ? (
          <div className="qa-welcome">
            <div className="qa-welcome__icon"><RobotOutlined /></div>
            <h1>开始一段学习对话</h1>
            <p>围绕当前课程提问，获取概念解释、学习建议与相关资源。</p>
            <div className={`qa-mode-row qa-mode-row--${mode}`}><button type="button" className={mode === 'quick' ? 'is-active' : ''} onClick={() => setMode('quick')}><BookOutlined /> 快速模式</button><button type="button" className={mode === 'expert' ? 'is-active' : ''} onClick={() => setMode('expert')}><SearchOutlined /> 专家模式</button></div>
          </div>
        ) : (
          <div className="qa-chat__stream" ref={listRef}>
            <List
              dataSource={visibleRecords}
              renderItem={(record) => <List.Item className="qa-turn">
                <div className="qa-message qa-message--user"><div className="qa-user-bubble"><span>{record.question}</span><div className="qa-message-actions"><button type="button" title="复制" onClick={() => void copyQuestion(record.question)}><CopyOutlined /></button><button type="button" title="编辑并重新发送" onClick={() => { setQuestion(record.question); setSelectedConversationId(getConversationId(record)) }}><EditOutlined /></button></div></div><Avatar icon={<UserOutlined />} /></div>
                {record.answer && <div className="qa-message qa-message--agent"><Avatar icon={<RobotOutlined />} /><div><Text>{record.answer}</Text>
                  {Array.isArray(record.metadata?.sources) && record.metadata.sources.length > 0 && <div className="qa-sources"><span>相关资料</span>{(record.metadata.sources as Array<{ source?: string; locator?: string }>).slice(0, 3).map((source, index) => <Tag key={`${source.source}-${source.locator}-${index}`} color="blue">{source.locator || source.source || `资料 ${index + 1}`}</Tag>)}</div>}
                </div></div>}
              </List.Item>}
            />
          </div>
        )}

        <div className="qa-composer">
          <TextArea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="输入你的学习问题…" autoSize={{ minRows: 2, maxRows: 5 }} onPressEnter={(event) => { if (!event.shiftKey) { event.preventDefault(); void handleSend() } }} />
          <div className="qa-composer__footer"><div className={`qa-composer__modes qa-composer__modes--${mode}`}><button type="button" className={mode === 'quick' ? 'is-active' : ''} onClick={() => setMode('quick')}><BookOutlined /> 快速模式</button><button type="button" className={mode === 'expert' ? 'is-active' : ''} onClick={() => setMode('expert')}><SearchOutlined /> 专家模式</button></div><Button type="primary" shape="circle" icon={<SendOutlined />} onClick={() => void handleSend()} loading={sending} aria-label="发送问题" /></div>
        </div>
      </section>
      {searchOpen && <div className="qa-search-overlay" role="dialog" aria-modal="true" aria-label="搜索问答历史" onClick={closeHistorySearch}>
        <section className="qa-search-dialog" onClick={(event) => event.stopPropagation()}>
          <div className="qa-search-dialog__input"><SearchOutlined /><Input autoFocus value={historyQuery} onChange={(event) => setHistoryQuery(event.target.value)} placeholder="搜索问答历史" bordered={false} /><button type="button" aria-label="关闭搜索" onClick={closeHistorySearch}>×</button></div>
          <div className="qa-search-dialog__results">
            {!historyQuery.trim() ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="输入关键词搜索问题或回答" /> : matchedRecords.length === 0 ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="没有匹配的消息" /> : matchedRecords.slice().reverse().map((record) => <button type="button" className="qa-search-result" key={record.id} onClick={() => { setSelectedConversationId(getConversationId(record)); closeHistorySearch() }}><RobotOutlined /><span><strong>{record.question}</strong><small>{record.answer || '暂无回答'}</small></span></button>)}
          </div>
        </section>
      </div>}
    </main>
  )
}

export default QAPage
