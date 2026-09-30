import { useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import type { GraphResponse } from '../api/types'

export function GraphView({ data, height = 600 }: { data: GraphResponse; height?: number }) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(800)

  useEffect(() => {
    const el = wrapRef.current
    if (!el) {
      return
    }
    const update = () => setWidth(el.clientWidth)
    update()
    const observer = new ResizeObserver(update)
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const graphData = useMemo(
    () => ({
      nodes: data.nodes.map((n) => ({
        id: String(n.id),
        name: n.name,
        label: n.label,
        color: n.label === 'Company' ? '#3b82f6' : n.label === 'EmailThread' ? '#a855f7' : '#10b981',
      })),
      links: data.edges.map((e) => ({
        source: String(e.source),
        target: String(e.target),
        label: e.type,
      })),
    }),
    [data],
  )

  return (
    <div ref={wrapRef} className="bg-slate-950 rounded border border-slate-800" style={{ height }}>
      <ForceGraph2D
        width={width}
        height={height}
        graphData={graphData}
        nodeLabel="name"
        nodeAutoColorBy="label"
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        linkLabel="label"
        nodeCanvasObject={(node: any, ctx, globalScale) => {
          const label = node.name
          const fontSize = 12 / globalScale
          ctx.font = `${fontSize}px Sans-Serif`
          ctx.fillStyle = node.color
          ctx.beginPath()
          ctx.arc(node.x || 0, node.y || 0, 5, 0, 2 * Math.PI)
          ctx.fill()
          ctx.fillStyle = '#e2e8f0'
          ctx.textAlign = 'center'
          ctx.fillText(label, node.x || 0, (node.y || 0) + 12)
        }}
      />
    </div>
  )
}
