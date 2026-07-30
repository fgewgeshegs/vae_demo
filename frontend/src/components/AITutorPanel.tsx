import React, { useRef, useState } from 'react'
import { Button, Card, Input, List, Space, Spin, Tag, Typography, message } from 'antd'
import { RobotOutlined, SendOutlined, ThunderboltOutlined, CodeOutlined, HighlightOutlined, FormOutlined } from '@ant-design/icons'
import { qaApi } from '../services/api'
import type { QARecord } from '../types'

const { Text, Paragraph } = Typography
const { TextArea } = Input

interface AITutorPanelProps {
  courseId?: number
  chapterTitle?: string
  kpTitle?: string
}

const quickActions = [
  { label: '总结本节', icon: <ThunderboltOutlined />, prompt: (kpTitle: string) => `请总结"${kpTitle}"这一节的核心内容` },
  { label: '解释代码', icon: <CodeOutlined />, prompt: () => '请解释本节中的关键代码' },
  { label: '提炼重点', icon: <HighlightOutlined />, prompt: (kpTitle: string) => `请提炼"${kpTitle}"的重点知识` },
  { label: '生成练习', icon: <FormOutlined />, prompt: (kpTitle: string) => `请为"${kpTitle}"生成几道练习题` },
]

const AITutorPanel: React.FC<AITutorPanelProps> = ({ courseId, chapterTitle, kpTitle }) => {
  const [records, setRecords] = useState<QARecord[]>([])
  const [question, setQuestion] = useState('')
  const [sending, setSending] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)

  const handleSend = async (text: string) => {
    if (!text.trim() || sending) return
    setSending(true)
    try {
      const res = await qaApi.ask(text.trim(), courseId, { source: 'tutor_panel' })
      setRecords((prev) => [...prev, res.data])
      setTimeout(() => {
        listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
      }, 100)
    } catch {
      message.error('发送失败，请稍后重试')
    } finally {
      setSending(false)
    }
  }

  const handleQuickAction = (action: typeof quickActions[0]) => {
    const p = action.prompt(kpTitle || chapterTitle || '本节')
    setQuestion(p)
    handleSend(p)
  }

  return (
    <Card
      size="small"
      title={
        <Space>
          <RobotOutlined style={{ color: '#7c3aed' }} />
          <Text strong>AI 智能辅导</Text>
        </Space>
      }
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        border: 'none',
        borderRadius: 0,
      }}
      styles={{ body: { flex: 1, display: 'flex', flexDirection: 'column', padding: '8px 12px', overflow: 'hidden' } }}
    >
      {/* Quick actions */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
        {quickActions.map((action) => (
          <Button
            key={action.label}
            size="small"
            icon={action.icon}
            onClick={() => handleQuickAction(action)}
            style={{ fontSize: 11, borderRadius: 6 }}
          >
            {action.label}
          </Button>
        ))}
      </div>

      {/* Chat messages */}
      <div
        ref={listRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          marginBottom: 8,
          paddingRight: 4,
        }}
      >
        {records.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px 12px' }}>
            <RobotOutlined style={{ fontSize: 28, color: '#c4b5fd' }} />
            <Paragraph type="secondary" style={{ marginTop: 8, fontSize: 12 }}>
              围绕当前课程提问，获取概念解释、学习建议与相关资源。
            </Paragraph>
          </div>
        ) : (
          <List
            dataSource={records}
            split={false}
            renderItem={(record) => (
              <div style={{ marginBottom: 12 }}>
                {/* User question */}
                <div style={{ textAlign: 'right', marginBottom: 4 }}>
                  <Tag color="blue" style={{ fontSize: 11, maxWidth: '80%', whiteSpace: 'normal', textAlign: 'left' }}>
                    {record.question}
                  </Tag>
                </div>
                {/* AI answer */}
                <div
                  style={{
                    background: '#f8fafc',
                    borderRadius: 8,
                    padding: '8px 10px',
                    border: '1px solid #e2e8f0',
                    maxHeight: 200,
                    overflowY: 'auto',
                  }}
                >
                  <Text style={{ fontSize: 12, whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                    {record.answer || record.ai_answer || '思考中...'}
                  </Text>
                </div>
              </div>
            )}
          />
        )}
      </div>

      {/* Input */}
      <div style={{ display: 'flex', gap: 8, borderTop: '1px solid #f1f5f9', paddingTop: 8 }}>
        <TextArea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onPressEnter={(e) => {
            if (!e.shiftKey) {
              e.preventDefault()
              handleSend(question)
              setQuestion('')
            }
          }}
          placeholder="输入问题..."
          autoSize={{ minRows: 1, maxRows: 3 }}
          style={{ fontSize: 12, flex: 1 }}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          loading={sending}
          onClick={() => {
            handleSend(question)
            setQuestion('')
          }}
          size="small"
        />
      </div>
    </Card>
  )
}

export default AITutorPanel
