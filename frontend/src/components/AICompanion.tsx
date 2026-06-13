import React, { useState, useEffect, useRef } from 'react'

const encouragements = [
  '状态不错，继续保持～',
  '每一点积累都在改变你。',
  '知识的边界，正在被你推远。',
  '专注本身就是一种力量。',
  '你比昨天又进步了一点。',
  '不要急，理解比速度重要。',
  '这个问题很有价值，继续深挖。',
  '休息一下，大脑也需要整理。',
  '你已经走了一段很长的路。',
  '好奇心是最高效的学习引擎。',
  '真正的理解来自反复的思考。',
  '每学会一个概念，就点亮一颗星。',
]

const moods = [
  '#06b6d4', '#6366f1', '#8b5cf6',
  '#ec4899', '#34d399', '#f59e0b',
]

const AICompanion: React.FC = () => {
  const [message, setMessage] = useState('你好，今天想学点什么？')
  const [visible, setVisible] = useState(true)
  const [mood, setMood] = useState(moods[1])
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    const cycle = () => {
      const next = encouragements[Math.floor(Math.random() * encouragements.length)]
      setMessage(next)
      setMood(moods[Math.floor(Math.random() * moods.length)])
      setVisible(true)
      timeoutRef.current = setTimeout(() => {
        setVisible(false)
        timeoutRef.current = setTimeout(cycle, 4000 + Math.random() * 6000)
      }, 5000 + Math.random() * 4000)
    }
    timeoutRef.current = setTimeout(cycle, 8000)
    return () => { if (timeoutRef.current) clearTimeout(timeoutRef.current) }
  }, [])

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      minHeight: 48,
    }}>
      <div className="animate-companion-float" style={{
        width: 36, height: 36, borderRadius: '50%',
        position: 'relative', flexShrink: 0,
      }}>
        <div style={{
          width: '100%', height: '100%', borderRadius: '50%',
          background: 'radial-gradient(circle at 35% 30%, ' + mood + ', #6366f1)',
          boxShadow: '0 0 20px ' + mood + '33, 0 0 40px ' + mood + '1a',
          transition: 'all 0.8s ease',
        }} />
        <div style={{ position: 'absolute', top: '35%', left: '28%', width: 4, height: 4, borderRadius: '50%', background: 'rgba(255,255,255,0.7)' }} />
        <div style={{ position: 'absolute', top: '35%', right: '28%', width: 4, height: 4, borderRadius: '50%', background: 'rgba(255,255,255,0.7)' }} />
        <div style={{ position: 'absolute', inset: -6, borderRadius: '50%', border: '1.5px solid ' + mood + '22', animation: 'breatheGlow 3s ease-in-out infinite' }} />
      </div>
      {visible && (
        <div className="animate-thought-appear" style={{
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid rgba(255,255,255,0.06)',
          borderRadius: '4px 14px 14px 14px',
          padding: '8px 14px',
          maxWidth: 220,
        }}>
          <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)', lineHeight: 1.5 }}>
            {message}
          </span>
        </div>
      )}
    </div>
  )
}

export default AICompanion