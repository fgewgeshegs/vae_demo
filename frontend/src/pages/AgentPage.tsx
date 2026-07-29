import React, { useState, useRef, useCallback, useEffect } from 'react'
import { Input, Button, Typography, Spin, Space, Avatar, message } from 'antd'
import { SendOutlined, ThunderboltOutlined, UserOutlined, RobotOutlined } from '@ant-design/icons'
import { chatApi } from '../services/api'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import WorkspacePageHeader from '../components/WorkspacePageHeader'

const { Text } = Typography
const { TextArea } = Input

interface ThinkingStep {
  label: string
  status: 'running' | 'done' | 'failed'
  tool?: string
  toolIcon?: string
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  thinkingSteps: ThinkingStep[]
  thinkingText: string
  thinkingExpanded: boolean
}

async function* parseSSE(response: Response): AsyncGenerator<any> {
  const reader = response.body?.getReader()
  if (!reader) throw new Error('Response body is not readable')
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      const lines = (buffer + decoder.decode()).split('\n')
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6).trim()
          if (dataStr) {
            try { yield JSON.parse(dataStr) } catch {}
          }
        }
      }
      break
    }
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''
    for (const part of parts) {
      const lines = part.split('\n')
      let eventData = ''
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          eventData = line.slice(6)
        }
      }
      if (eventData) {
        try { yield JSON.parse(eventData) } catch {}
      }
    }
  }
}

const ThinkingProcess: React.FC<{
  steps: ThinkingStep[]
  thinkingText: string
  expanded: boolean
  onToggle: () => void
}> = ({ steps, thinkingText, expanded, onToggle }) => {
  const runningCount = steps.filter(s => s.status === 'running').length
  const isActive = runningCount > 0
  const statusIcon = isActive ? '\u23f3' : '\u2705'
  const hasThinking = thinkingText.length > 0

  return (
    <div style={{
      background: '#f8fafc',
      border: '1px solid #e2e8f0',
      borderRadius: 8,
      marginBottom: 12,
      overflow: 'hidden',
    }}>
      <div
        onClick={onToggle}
        style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '6px 12px', cursor: 'pointer', userSelect: 'none',
          fontSize: 12, color: '#64748b',
        }}
      >
        <span>{statusIcon}</span>
        <span style={{ fontWeight: 500, flex: 1 }}>思考过程</span>
        <span style={{ fontSize: 11, color: '#94a3b8' }}>
          {steps.length} 步{isActive ? ' \u00b7 进行中' : ''}{hasThinking ? ` \u00b7 ${thinkingText.length} 字` : ''}
        </span>
        <span style={{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>
          \u25be
        </span>
      </div>
      {expanded && (
        <div style={{ padding: '4px 12px 10px', borderTop: '1px solid #f1f5f9' }}>
          {steps.map((step, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '4px 0', fontSize: 12,
              color: step.status === 'failed' ? '#ef4444' : step.status === 'running' ? '#2563eb' : '#475569',
            }}>
              <span style={{ width: 16, textAlign: 'center' }}>
                {step.status === 'done' ? '\u2713' : step.status === 'running' ? '\u27f3' : step.status === 'failed' ? '\u2717' : '\u25cb'}
              </span>
              <span>{step.toolIcon || ''}{step.label}</span>
              {step.status === 'running' && <Spin size="small" style={{ marginLeft: 4 }} />}
            </div>
          ))}
          {hasThinking && (
            <div style={{
              marginTop: 8, padding: '8px 10px',
              background: '#f1f5f9', borderRadius: 6,
              fontSize: 12, color: '#475569',
              lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
              maxHeight: 200, overflow: 'auto',
            }}>
              {thinkingText}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const MarkdownContent: React.FC<{ content: string }> = ({ content }) => (
  <div className="agent-markdown">
    <ReactMarkdown remarkPlugins={[remarkGfm]}>
      {content}
    </ReactMarkdown>
  </div>
)

const markdownStyles = `
  .agent-markdown h1, .agent-markdown h2, .agent-markdown h3,
  .agent-markdown h4, .agent-markdown h5, .agent-markdown h6 {
    margin: 0.6em 0 0.3em; font-weight: 600; line-height: 1.35;
    color: #0f172a;
  }
  .agent-markdown h1 { font-size: 1.25em; }
  .agent-markdown h2 { font-size: 1.15em; }
  .agent-markdown h3 { font-size: 1.05em; }
  .agent-markdown p { margin: 0.4em 0; }
  .agent-markdown ul, .agent-markdown ol { padding-left: 1.6em; margin: 0.3em 0; }
  .agent-markdown li { margin: 0.2em 0; }
  .agent-markdown code { font-size: 0.9em; padding: 1px 5px; border-radius: 4px; background: #f1f5f9; color: #0f172a; }
  .agent-markdown pre { margin: 0.5em 0; padding: 10px 14px; border-radius: 8px; background: #1e293b; overflow-x: auto; }
  .agent-markdown pre code { padding: 0; background: transparent; color: #e2e8f0; }
  .agent-markdown blockquote { margin: 0.4em 0; padding: 2px 0 2px 12px; border-left: 3px solid #e2e8f0; color: #64748b; }
  .agent-markdown table { border-collapse: collapse; margin: 0.5em 0; width: 100%; }
  .agent-markdown th, .agent-markdown td { border: 1px solid #e2e8f0; padding: 6px 10px; text-align: left; font-size: 0.95em; }
  .agent-markdown th { background: #f8fafc; font-weight: 600; }
  .agent-markdown a { color: #2563eb; text-decoration: underline; }
  .agent-markdown hr { margin: 0.7em 0; border: none; border-top: 1px solid #e2e8f0; }
  .agent-markdown img { max-width: 100%; border-radius: 6px; }
`


const ChatBubble: React.FC<{
  role: 'user' | 'assistant'
  content: string
  thinkingSteps?: ThinkingStep[]
  thinkingText?: string
  thinkingExpanded?: boolean
  onToggleThinking?: () => void
  isStreaming?: boolean
}> = ({ role, content, thinkingSteps, thinkingText, thinkingExpanded, onToggleThinking, isStreaming }) => {
  const isUser = role === 'user'
  return (
    <div style={{
      display: 'flex', gap: 10, marginBottom: 20,
      flexDirection: isUser ? 'row-reverse' : 'row',
      alignItems: 'flex-start',
    }}>
      <Avatar
        icon={isUser ? <UserOutlined /> : <RobotOutlined />}
        style={{
          background: isUser ? 'linear-gradient(135deg, #00a7c2, #4169e1)' : 'linear-gradient(135deg, #7c5bd6, #c85ea8)',
          flexShrink: 0, marginTop: 4,
        }}
      />
      <div style={{ maxWidth: '75%', minWidth: 0 }}>
        {!isUser && thinkingSteps && thinkingSteps.length > 0 && onToggleThinking && (
          <ThinkingProcess steps={thinkingSteps} thinkingText={thinkingText || ''} expanded={thinkingExpanded ?? false} onToggle={onToggleThinking} />
        )}
        <div style={{
          background: isUser ? 'linear-gradient(135deg, #00a7c2, #4169e1)' : '#ffffff',
          color: isUser ? '#fff' : '#0f172a',
          padding: '10px 16px',
          borderRadius: 12,
          borderBottomRightRadius: isUser ? 4 : 12,
          borderBottomLeftRadius: isUser ? 12 : 4,
          border: isUser ? 'none' : '1px solid #e2e8f0',
          boxShadow: isUser ? 'none' : '0 1px 4px rgba(0,0,0,0.04)',
          lineHeight: 1.7, fontSize: 13, wordBreak: 'break-word',
        }}>
          {isUser
            ? <span style={{ whiteSpace: 'pre-wrap' }}>{content || null}</span>
            : content
              ? <MarkdownContent content={content} />
              : isStreaming ? <span style={{ opacity: 0.5 }}>正在思考...</span> : null
          }
        </div>
      </div>
    </div>
  )
}

const AgentPage: React.FC = () => {
  const [conversation, setConversation] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [currentThinking, setCurrentThinking] = useState<ThinkingStep[]>([])
  const [currentThinkingText, setCurrentThinkingText] = useState('')
  const [currentContent, setCurrentContent] = useState('')
  const [hasWelcome, setHasWelcome] = useState(true)
  const listRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [conversation, currentContent, currentThinkingText])

  const commitAssistantMessage = useCallback((steps: ThinkingStep[], thinkingText: string, content: string) => {
    setConversation(prev => [...prev, {
      role: 'assistant', content,
      thinkingSteps: steps, thinkingText, thinkingExpanded: true,
    }])
    setCurrentThinking([])
    setCurrentThinkingText('')
    setCurrentContent('')
  }, [])

  const toggleThinking = useCallback((msgIndex: number) => {
    setConversation(prev => prev.map((msg, i) =>
      i === msgIndex ? { ...msg, thinkingExpanded: !msg.thinkingExpanded } : msg
    ))
  }, [])

  const handleSend = useCallback(async () => {
    const text = input.trim()
    if (!text || streaming) return
    setInput('')
    setHasWelcome(false)
    setConversation(prev => [...prev, { role: 'user', content: text, thinkingSteps: [], thinkingText: '', thinkingExpanded: false }])
    setStreaming(true)
    setCurrentThinking([])
    setCurrentThinkingText('')
    setCurrentContent('')

    const abortController = new AbortController()
    abortRef.current = abortController

    try {
      const response = await chatApi.agentStream(text)
      if (!response.ok || !response.body) {
        throw new Error('HTTP ' + response.status)
      }

      let collectedSteps: ThinkingStep[] = []
      let collectedThinkingText = ''
      let collectedContent = ''

      for await (const event of parseSSE(response)) {
        switch (event.type) {
          case 'thinking':
          case 'tool_start':
          case 'tool_end':
            if (event.steps) {
              collectedSteps = event.steps
              setCurrentThinking([...event.steps])
            }
            break
          case 'thinking_delta':
            collectedThinkingText += event.content || ''
            setCurrentThinkingText(collectedThinkingText)
            break
          case 'answer_delta':
            collectedContent += event.content || ''
            setCurrentContent(collectedContent)
            break
          case 'message':
            collectedContent = event.content || ''
            setCurrentContent(collectedContent)
            break
          case 'error':
            message.error(event.content || event.detail || '处理出错')
            break
        }
      }
      commitAssistantMessage(collectedSteps, collectedThinkingText, collectedContent)
    } catch (err: any) {
      if (err.name === 'AbortError') return
      message.error('Agent 请求失败：' + (err?.message || '未知错误'))
    } finally {
      setStreaming(false)
      abortRef.current = null
    }
  }, [input, streaming, commitAssistantMessage])

  const handleCancel = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
    }
    setStreaming(false)
    setCurrentThinking([])
    setCurrentThinkingText('')
    setCurrentContent('')
  }, [])

  return (
    <div className="workspace-page workspace-page--agent" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 150px)' }}>
      <WorkspacePageHeader title="全局 Agent" description="统一协调知识库、学习画像、路径、资源与评估任务。" metrics={[{ label: '会话消息', value: conversation.length }]} />
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <ThunderboltOutlined style={{ fontSize: 20, color: '#7c5bd6' }} />
          <Text strong style={{ fontSize: 16 }}>全局 Agent</Text>
          {streaming && (
            <Button size="small" danger onClick={handleCancel} style={{ marginLeft: 'auto', fontSize: 11 }}>
              取消
            </Button>
          )}
        </div>
        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 2 }}>
          向主 Agent 提问，它将自动调用知识库、画像、路径、资源和评估工具
        </Text>
      </div>

      <div className="conversation-panel" ref={listRef} style={{
        flex: 1, overflow: 'auto', padding: 16,
        background: 'rgba(255, 255, 255, 0.64)',
        border: '1px solid rgba(72, 102, 153, 0.14)',
        borderRadius: 8, marginBottom: 12,
        boxShadow: '0 18px 50px rgba(42,68,112,0.08)',
      }}>
        {hasWelcome && conversation.length === 0 && (
          <div style={{ textAlign: 'center', paddingTop: 60, color: '#94a3b8' }}>
            <ThunderboltOutlined style={{ fontSize: 40, color: '#cbd5e1', marginBottom: 16 }} />
            <div style={{ fontSize: 15, color: '#64748b', marginBottom: 8 }}>全局 Agent</div>
            <div style={{ fontSize: 12, lineHeight: 1.8 }}>
              <div>试试以下功能：</div>
              <div style={{ marginTop: 4 }}>"更新我的学习画像"</div>
              <div>"生成个性化学习路径"</div>
              <div>"给我生成 Java 的思维导图"</div>
              <div>"评估我的学习效果"</div>
              <div>"解释一下什么是多态"</div>
            </div>
          </div>
        )}

        {/* Markdown styles injected once */}
        <style>{markdownStyles}</style>

        {conversation.map((msg, i) => (
          <ChatBubble key={i} role={msg.role} content={msg.content}
            thinkingSteps={msg.thinkingSteps} thinkingText={msg.thinkingText} thinkingExpanded={msg.thinkingExpanded}
            onToggleThinking={() => toggleThinking(i)} />
        ))}

        {streaming && (
          <ChatBubble role="assistant" content={currentContent}
            thinkingSteps={currentThinking} thinkingText={currentThinkingText} thinkingExpanded={true}
            onToggleThinking={() => {}} isStreaming={!currentContent} />
        )}
      </div>

      <Space.Compact style={{ width: '100%' }}>
        <TextArea value={input} onChange={(e) => setInput(e.target.value)}
          placeholder="向 Agent 提问..."
          autoSize={{ minRows: 1, maxRows: 4 }} disabled={streaming}
          onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); handleSend() } }}
          style={{ background: '#f8fafc', border: '1px solid #e2e8f0', color: '#0f172a', fontSize: 13, borderRadius: '6px 0 0 6px', resize: 'none' }}
        />
        <Button type="primary" icon={<SendOutlined />} onClick={handleSend}
          loading={streaming} disabled={!input.trim() || streaming}
          style={{ height: 'auto' }}>
          {streaming ? '处理中' : '发送'}
        </Button>
      </Space.Compact>
    </div>
  )
}

export default AgentPage

