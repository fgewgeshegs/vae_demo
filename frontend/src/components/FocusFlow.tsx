import React from 'react'

interface FocusFlowProps {
  focusScore?: number
  sessionMinutes?: number
  streakDays?: number
}

const FocusFlow: React.FC<FocusFlowProps> = ({
  focusScore = 72,
  sessionMinutes = 28,
  streakDays = 5,
}) => {
  const r = 60
  const circumference = 2 * Math.PI * r
  const offset = circumference - (focusScore / 100) * circumference

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      padding: '20px 0 16px',
    }}>
      <div style={{ position: 'relative', width: 160, height: 160 }}>
        <svg width={160} height={160} viewBox='0 0 160 160'>
          <circle cx={80} cy={80} r={76}
            fill='none' stroke='rgba(99,102,241,0.04)' strokeWidth={0.5}
            strokeDasharray='4 4'
          />
          <circle cx={80} cy={80} r={r}
            fill='none' stroke='rgba(255,255,255,0.04)' strokeWidth={8}
          />
          <circle cx={80} cy={80} r={r - 14}
            fill='none' stroke='rgba(99,102,241,0.03)' strokeWidth={2}
            strokeDasharray='2 4'
          />
          <circle cx={80} cy={80} r={r}
            fill='none' stroke='url(#focus-gradient)' strokeWidth={8}
            strokeLinecap='round'
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            transform='rotate(-90, 80, 80)'
            style={{ transition: 'stroke-dashoffset 1.5s cubic-bezier(0.19,1,0.22,1)' }}
          />
          <defs>
            <linearGradient id='focus-gradient' x1='0%' y1='0%' x2='100%' y2='100%'>
              <stop offset='0%' stopColor='#06b6d4' />
              <stop offset='50%' stopColor='#6366f1' />
              <stop offset='100%' stopColor='#8b5cf6' />
            </linearGradient>
          </defs>
          <g style={{ animation: 'orbit 8s linear infinite', transformOrigin: '80px 80px' }}>
            <circle cx={80} cy={8} r={2.5} fill='#06b6d4' opacity={0.5}>
              <animate attributeName='opacity' values='0.3;0.7;0.3' dur='2s' repeatCount='indefinite' />
            </circle>
          </g>
          <g style={{ animation: 'orbitReverse 12s linear infinite', transformOrigin: '80px 80px' }}>
            <circle cx={80} cy={10} r={1.8} fill='#8b5cf6' opacity={0.4}>
              <animate attributeName='opacity' values='0.2;0.6;0.2' dur='2.5s' repeatCount='indefinite' />
            </circle>
          </g>
        </svg>
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
        }}>
          <span style={{
            fontSize: 32, fontWeight: 700,
            background: 'linear-gradient(135deg, #06b6d4, #818cf8)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            lineHeight: 1,
          }}>
            {focusScore}
          </span>
          <span style={{
            fontSize: 10, color: 'rgba(255,255,255,0.25)',
            letterSpacing: 1.5, textTransform: 'uppercase',
            marginTop: 2,
          }}>
            {'\u5fc3'}{'\u6d41'}{'\u6307'}{'\u6570'}
          </span>
        </div>
      </div>
      <div style={{
        display: 'flex', gap: 24, marginTop: 16,
        justifyContent: 'center',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            fontSize: 16, fontWeight: 600,
            color: 'rgba(255,255,255,0.80)',
          }}>
            {sessionMinutes}
          </div>
          <div style={{
            fontSize: 9, color: 'rgba(255,255,255,0.20)',
            letterSpacing: 1, textTransform: 'uppercase',
            marginTop: 1,
          }}>
            {'\u4eca'}{'\u65e5'}{'\u5206'}{'\u949f'}
          </div>
        </div>
        <div style={{
          width: 1, alignSelf: 'stretch',
          background: 'rgba(255,255,255,0.06)',
        }} />
        <div style={{ textAlign: 'center' }}>
          <div style={{
            fontSize: 16, fontWeight: 600,
            color: 'rgba(255,255,255,0.80)',
          }}>
            {streakDays}
          </div>
          <div style={{
            fontSize: 9, color: 'rgba(255,255,255,0.20)',
            letterSpacing: 1, textTransform: 'uppercase',
            marginTop: 1,
          }}>
            {'\u8fde'}{'\u7eed'}{'\u5929'}{'\u6570'}
          </div>
        </div>
      </div>
    </div>
  )
}

export default FocusFlow