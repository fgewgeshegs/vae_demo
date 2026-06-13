import React, { useMemo } from 'react'

interface Star {
  cx: number; cy: number; r: number; label: string
  connections: number[]; delay: number; color: string
}

const subjects = [
  { label: '\u6570\u5b66', color: '#06b6d4', size: 3.5 },
  { label: '\u7f16\u7a0b', color: '#6366f1', size: 4 },
  { label: '\u82f1\u8bed', color: '#8b5cf6', size: 3 },
  { label: '\u7269\u7406', color: '#ec4899', size: 3.2 },
  { label: '\u5386\u53f2', color: '#f59e0b', size: 2.8 },
  { label: '\u5316\u5b66', color: '#34d399', size: 2.8 },
  { label: '\u751f\u7269', color: '#14b8a6', size: 2.5 },
  { label: 'AI', color: '#f472b6', size: 4.5 },
]

const KnowledgeConstellation: React.FC<{ insights?: string }> = ({ insights }) => {
  const stars: Star[] = useMemo(() => {
    const cx = 180, cy = 130, radius = 100
    return subjects.map((s, i) => {
      const angle = (i / subjects.length) * Math.PI * 2 - Math.PI / 2
      const dist = radius * (0.6 + Math.random() * 0.4)
      return {
        cx: cx + Math.cos(angle) * dist,
        cy: cy + Math.sin(angle) * dist,
        r: s.size,
        label: s.label,
        color: s.color,
        delay: i * 0.4,
        connections: [],
      }
    })
  }, [])

  const edges = useMemo(() => {
    const pairs: [number, number][] = []
    const related = [[0,1],[0,3],[1,6],[1,7],[2,4],[2,5],[3,0],[3,6],[4,2],[5,1],[6,3],[7,1]]
    for (const [a, b] of related) {
      if (a < stars.length && b < stars.length) pairs.push([a, b])
    }
    return pairs
  }, [stars])

  return (
    <div style={{
      position: 'relative',
      width: '100%', height: 280,
      overflow: 'hidden',
    }}>
      <svg width="100%" height="100%" viewBox="0 0 360 260"
        style={{ filter: 'drop-shadow(0 0 2px rgba(99,102,241,0.08))' }}
      >
        <defs>
          <radialGradient id="star-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#6366f1" stopOpacity="0.15" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
          </radialGradient>
        </defs>
        <ellipse cx={180} cy={130} rx={110} ry={60}
          fill="none" stroke="rgba(99,102,241,0.04)" strokeWidth={0.5}
          transform="rotate(-15, 180, 130)"
        />
        <ellipse cx={180} cy={130} rx={80} ry={45}
          fill="none" stroke="rgba(6,182,212,0.03)" strokeWidth={0.5}
          transform="rotate(10, 180, 130)"
        />
        <circle cx={180} cy={130} r={16} fill="url(#star-glow)" />
        <circle cx={180} cy={130} r={3} fill="rgba(160,170,255,0.25)">
          <animate attributeName="r" values="2;4;2" dur="3s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.2;0.6;0.2" dur="3s" repeatCount="indefinite" />
        </circle>
        {edges.map(([a, b], i) => {
          const s1 = stars[a], s2 = stars[b]
          if (!s1 || !s2) return null
          return (
            <g key={'edge-' + i} style={{ animation: 'constellate 0.6s ease-out ' + Math.min(s1.delay, s2.delay) + 's both' }}>
              <line x1={s1.cx} y1={s1.cy} x2={s2.cx} y2={s2.cy}
                stroke="rgba(99,102,241,0.08)" strokeWidth={0.8}
              />
              <circle r={2} fill="#06b6d4" opacity={0.4}>
                <animateMotion dur={'' + (3 + i % 3) + 's'} repeatCount='indefinite'
                  path={'M' + s1.cx + ',' + s1.cy + ' L' + s2.cx + ',' + s2.cy}
                />
              </circle>
            </g>
          )
        })}
        {stars.map((star, i) => (
          <g key={i} style={{ animation: 'constellate 0.5s ease-out ' + star.delay + 's both' }}>
            <circle cx={star.cx} cy={star.cy} r={star.r * 3} fill={star.color} opacity={0.06}>
              <animate attributeName='opacity' values='0.04;0.1;0.04' dur={'' + (2 + i % 3) + 's'} repeatCount='indefinite' />
            </circle>
            <circle cx={star.cx} cy={star.cy} r={star.r} fill={star.color} opacity={0.7}>
              <animate attributeName='opacity' values='0.5;0.9;0.5' dur={'' + (2 + i % 3) + 's'} repeatCount='indefinite' />
              <animate attributeName='r' values={star.r + ';' + (star.r * 1.3) + ';' + star.r}
                dur={'' + (2.5 + i % 2) + 's'} repeatCount='indefinite'
              />
            </circle>
            <text x={star.cx} y={star.cy + star.r + 12}
              textAnchor="middle" fill="rgba(255,255,255,0.25)"
              fontSize={9} fontWeight={500} letterSpacing={1}
            >
              {star.label}
            </text>
          </g>
        ))}
      </svg>
      {insights && (
        <div style={{
          position: 'absolute', bottom: 4, left: 0, right: 0,
          textAlign: 'center',
        }}>
          <span style={{
            fontSize: 11, color: 'rgba(255,255,255,0.18)',
            letterSpacing: 0.5,
          }}>
            {insights}
          </span>
        </div>
      )}
    </div>
  )
}

export default KnowledgeConstellation