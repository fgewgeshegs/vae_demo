import React, { useState } from 'react'
import { Input, message } from 'antd'
import { PlusOutlined, BulbOutlined } from '@ant-design/icons'

const { TextArea } = Input

const QuickThoughtFAB: React.FC = () => {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')

  const handleSubmit = () => {
    if (!text.trim()) return
    message.success({
      icon: <BulbOutlined style={{ color: '#fbbf24' }} />,
      content: '\u60f3\u6cd5\u5df2\u8bb0\u5f55 \u2728',
      duration: 2,
    })
    setText('')
    setOpen(false)
  }

  return (
    <>
      <div
        onClick={() => setOpen(!open)}
        style={{
          position: 'fixed', bottom: 32, right: 32, zIndex: 999,
          width: 44, height: 44, borderRadius: '50%',
          background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
          boxShadow: '0 4px 20px rgba(99,102,241,0.3), 0 0 40px rgba(99,102,241,0.1)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer',
          transition: 'all 0.35s cubic-bezier(0.19,1,0.22,1)',
          transform: open ? 'rotate(45deg)' : 'rotate(0deg)',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.transform = open ? 'rotate(45deg) scale(1.1)' : 'scale(1.1)'; e.currentTarget.style.boxShadow = '0 6px 28px rgba(99,102,241,0.4)' }}
        onMouseLeave={(e) => { e.currentTarget.style.transform = open ? 'rotate(45deg)' : 'scale(1)'; e.currentTarget.style.boxShadow = '0 4px 20px rgba(99,102,241,0.3)' }}
      >
        <PlusOutlined style={{ color: 'white', fontSize: 18 }} />
      </div>
      {open && (
        <>
          <div
            onClick={() => setOpen(false)}
            style={{
              position: 'fixed', inset: 0, zIndex: 998,
              background: 'rgba(0,0,0,0.3)',
              backdropFilter: 'blur(2px)',
            }}
          />
          <div className='animate-thought-appear' style={{
            position: 'fixed', bottom: 88, right: 32, zIndex: 999,
            width: 280,
            background: 'rgba(20,27,45,0.95)',
            backdropFilter: 'blur(16px)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 14,
            padding: 16,
            boxShadow: '0 8px 40px rgba(0,0,0,0.5)',
          }}>
            <div style={{
              fontSize: 11, fontWeight: 600, letterSpacing: 1,
              color: 'rgba(255,255,255,0.20)', textTransform: 'uppercase',
              marginBottom: 10,
            }}>
              <BulbOutlined style={{ marginRight: 6 }} />
              {'\u8bb0'}{'\u4e00'}{'\u4e2a'}{'\u60f3'}{'\u6cd5'}
            </div>
            <TextArea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder='\u60f3\u5230\u4e86\u4ec0\u4e48\uff1f'
              autoSize={{ minRows: 2, maxRows: 5 }}
              style={{
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.08)',
                color: 'rgba(255,255,255,0.80)',
                fontSize: 13,
                borderRadius: 8,
                resize: 'none',
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSubmit()
                }
              }}
            />
            <div style={{
              display: 'flex', justifyContent: 'flex-end', marginTop: 10,
            }}>
              <div
                onClick={handleSubmit}
                style={{
                  padding: '6px 16px', borderRadius: 8,
                  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                  color: 'white', fontSize: 12, fontWeight: 600,
                  cursor: 'pointer', letterSpacing: 1,
                  transition: 'opacity 0.2s',
                  opacity: text.trim() ? 1 : 0.4,
                }}
              >
                {'\u8bb0'}{'\u5f55'}
              </div>
            </div>
          </div>
        </>
      )}
    </>
  )
}

export default QuickThoughtFAB