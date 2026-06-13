import React, { useMemo } from 'react'

const LearningRhythm: React.FC = () => {
  const bars = useMemo(() => {
    return Array.from({ length: 48 }, (_, i) => {
      const hour = (i / 2)
      const base = hour >= 8 && hour <= 22
        ? 0.4 + 0.6 * Math.sin((hour - 8) / 14 * Math.PI)
        : 0.05 + Math.random() * 0.1
      const noise = 0.3 + Math.random() * 0.7
      return Math.min(1, base * noise * 1.2)
    })
  }, [])

  const now = new Date().getHours() + new Date().getMinutes() / 60

  return (
    <div style={{ padding: '16px 0 8px' }}>
      <svg width='100%' height={64} viewBox='0 0 480 64'
        style={{ filter: 'drop-shadow(0 0 4px rgba(99,102,241,0.05))' }}
      >
        <defs>
          <linearGradient id='bar-grad' x1='0' y1='0' x2='0' y2='1'>
            <stop offset='0%' stopColor='#06b6d4' stopOpacity={0.6} />
            <stop offset='100%' stopColor='#6366f1' stopOpacity={0.15} />
          </linearGradient>
        </defs>
        {bars.map((val, i) => {
          const x = i * 10
          const h = Math.max(4, val * 48)
          const isNow = Math.abs(i / 2 - now) < 0.5
          return (
            <g key={i}>
              <rect
                x={x} y={56 - h}
                width={6} height={h}
                rx={3} ry={3}
                fill={isNow ? 'url(#bar-grad)' : 'rgba(99,102,241,0.12)'}
                style={{
                  transition: 'all 0.5s ease',
                  animation: 'waveRise 0.5s ease-out ' + (i * 0.03) + 's both',
                }}
              />
              {isNow && (
                <>
                  <rect
                    x={x - 1} y={56 - h - 2}
                    width={8} height={h + 4}
                    rx={4} ry={4}
                    fill='none'
                    stroke='#06b6d4'
                    strokeWidth={1}
                    opacity={0.5}
                    style={{ animation: 'breatheGlow 2s ease-in-out infinite' }}
                  />
                  <circle cx={x + 3} cy={56 - h - 6} r={2} fill='#06b6d4' opacity={0.6}>
                    <animate attributeName='opacity' values='0.3;0.8;0.3' dur='2s' repeatCount='indefinite' />
                  </circle>
                </>
              )}
            </g>
          )
        })}
        <line x1={0} y1={56} x2={480} y2={56}
          stroke='rgba(255,255,255,0.03)' strokeWidth={0.5}
        />
      </svg>
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        padding: '0 2px', marginTop: 4,
      }}>
        {['00','04','08','12','16','20','24'].map((t) => (
          <span key={t} style={{
            fontSize: 9, color: 'rgba(255,255,255,0.15)',
            letterSpacing: 0.5,
          }}>
            {t}
          </span>
        ))}
      </div>
    </div>
  )
}

export default LearningRhythm