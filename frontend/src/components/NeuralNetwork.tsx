import React, { useRef, useEffect, useCallback } from 'react'

interface Node {
  x: number; y: number; vx: number; vy: number
  radius: number; phase: number; connections: number[]
}

interface Signal {
  from: number; to: number; progress: number; speed: number
}

const NeuralNetwork: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const nodesRef = useRef<Node[]>([])
  const signalsRef = useRef<Signal[]>([])
  const mouseRef = useRef({ x: -9999, y: -9999 })
  const animIdRef = useRef(0)

  const initNodes = useCallback((w: number, h: number) => {
    const count = Math.floor((w * h) / 55000)
    const nodes: Node[] = []
    for (let i = 0; i < Math.max(count, 24); i++) {
      nodes.push({
        x: Math.random() * w, y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.25, vy: (Math.random() - 0.5) * 0.25,
        radius: 1.5 + Math.random() * 2.5,
        phase: Math.random() * Math.PI * 2,
        connections: [],
      })
    }
    for (let i = 0; i < nodes.length; i++) {
      const conns: number[] = []
      for (let j = 0; j < nodes.length; j++) {
        if (i === j) continue
        const dx = nodes[i].x - nodes[j].x, dy = nodes[i].y - nodes[j].y
        if (Math.sqrt(dx*dx + dy*dy) < Math.min(w, h) * 0.25) conns.push(j)
      }
      nodes[i].connections = conns.slice(0, 4)
    }
    nodesRef.current = nodes
  }, [])

  const fireSignal = useCallback(() => {
    const nodes = nodesRef.current
    if (nodes.length < 2) return
    let from = Math.floor(Math.random() * nodes.length)
    const conns = nodes[from].connections
    if (conns.length === 0) return
    const to = conns[Math.floor(Math.random() * conns.length)]
    signalsRef.current.push({
      from, to,
      progress: 0,
      speed: 0.015 + Math.random() * 0.02,
    })
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const resize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
      initNodes(canvas.width, canvas.height)
    }
    resize()
    window.addEventListener('resize', resize)

    const handleMouse = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY }
    }
    window.addEventListener('mousemove', handleMouse)

    let lastFire = 0
    const draw = (time: number) => {
      const w = canvas.width, h = canvas.height
      ctx.clearRect(0, 0, w, h)

      const nodes = nodesRef.current
      const signals = signalsRef.current
      const mouse = mouseRef.current

      if (time - lastFire > 800 + Math.random() * 1200) {
        fireSignal()
        lastFire = time
      }

      for (const n of nodes) {
        n.x += n.vx
        n.y += n.vy
        const dx = n.x - mouse.x, dy = n.y - mouse.y
        const dist = Math.sqrt(dx*dx + dy*dy)
        if (dist < 200) {
          const force = (200 - dist) / 200 * 1.5
          n.x += (dx / dist) * force
          n.y += (dy / dist) * force
        }
        if (n.x < -20) n.x = w + 20
        if (n.x > w + 20) n.x = -20
        if (n.y < -20) n.y = h + 20
        if (n.y > h + 20) n.y = -20
      }

      for (const n of nodes) {
        for (const ci of n.connections) {
          const target = nodes[ci]
          if (!target) continue
          const dx = n.x - target.x, dy = n.y - target.y
          const dist = Math.sqrt(dx*dx + dy*dy)
          if (dist > Math.min(w, h) * 0.35) continue
          const alpha = Math.max(0, 0.12 * (1 - dist / (Math.min(w, h) * 0.35)))
          ctx.beginPath()
          ctx.moveTo(n.x, n.y)
          ctx.lineTo(target.x, target.y)
          ctx.strokeStyle = `rgba(99, 102, 241, ${alpha})`
          ctx.lineWidth = 0.6
          ctx.stroke()
        }
      }

      for (let i = signals.length - 1; i >= 0; i--) {
        const s = signals[i]
        s.progress += s.speed
        if (s.progress >= 1) { signals.splice(i, 1); continue }
        const from = nodes[s.from], to = nodes[s.to]
        if (!from || !to) { signals.splice(i, 1); continue }
        const x = from.x + (to.x - from.x) * s.progress
        const y = from.y + (to.y - from.y) * s.progress
        const pulseAlpha = Math.sin(s.progress * Math.PI) * 0.8
        ctx.beginPath()
        ctx.arc(x, y, 2.5, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(6, 182, 212, ${pulseAlpha})`
        ctx.fill()
        ctx.beginPath()
        ctx.arc(x, y, 5, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(6, 182, 212, ${pulseAlpha * 0.25})`
        ctx.fill()
      }

      for (const n of nodes) {
        const pulse = 0.6 + 0.4 * Math.sin(time * 0.001 + n.phase)
        const r = n.radius * (0.8 + 0.2 * pulse)
        const grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, r * 4)
        grad.addColorStop(0, `rgba(99, 102, 241, ${0.15 * pulse})`)
        grad.addColorStop(1, 'rgba(99, 102, 241, 0)')
        ctx.beginPath()
        ctx.arc(n.x, n.y, r * 4, 0, Math.PI * 2)
        ctx.fillStyle = grad
        ctx.fill()
        ctx.beginPath()
        ctx.arc(n.x, n.y, r, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(160, 170, 255, ${0.5 + 0.3 * pulse})`
        ctx.fill()
      }

      animIdRef.current = requestAnimationFrame(draw)
    }
    animIdRef.current = requestAnimationFrame(draw)

    return () => {
      cancelAnimationFrame(animIdRef.current)
      window.removeEventListener('resize', resize)
      window.removeEventListener('mousemove', handleMouse)
    }
  }, [initNodes, fireSignal])

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed', inset: 0, zIndex: 0,
        pointerEvents: 'none',
        opacity: 0.6,
      }}
    />
  )
}

export default NeuralNetwork
