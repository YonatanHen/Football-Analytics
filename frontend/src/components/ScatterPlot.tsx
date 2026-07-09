import { useEffect, useMemo, useRef, useState } from 'react'
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine,
} from 'recharts'
import type { ScatterPoint } from '../api/players'

interface ScatterPlotProps {
  data: ScatterPoint[]
  onPointClick?: (point: ScatterPoint) => void
}

const POSITION_COLORS: Record<string, string> = {
  GK: '#6366f1', DF: '#22c55e', MF: '#f59e0b', FW: '#ef4444',
}

const Y_AXIS_WIDTH = 55
const MARGIN = { top: 24, right: 24, bottom: 44, left: 8 }
const MIN_ZOOM_FRACTION = 0.03 // don't let a single wheel-zoom session collapse past 3% of the full domain

type Domain = [number, number]

function clampWidth(width: number, full: Domain): number {
  const fullWidth = full[1] - full[0]
  return Math.min(fullWidth, Math.max(fullWidth * MIN_ZOOM_FRACTION, width))
}

// Shift a domain window back inside the full data range, preserving its width —
// used to stop panning past the edges of the actual data.
function clampDomain(domain: Domain, full: Domain): Domain {
  const width = domain[1] - domain[0]
  let [lo, hi] = domain
  if (lo < full[0]) { lo = full[0]; hi = lo + width }
  if (hi > full[1]) { hi = full[1]; lo = hi - width }
  return [lo, hi]
}

export default function ScatterPlot({ data, onPointClick }: ScatterPlotProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [xDomain, setXDomain] = useState<Domain | null>(null)
  const [yDomain, setYDomain] = useState<Domain | null>(null)

  const byPosition = useMemo(() => {
    const grouped: Record<string, ScatterPoint[]> = {}
    for (const p of data) {
      const pos = p.position || 'MF'
      grouped[pos] = grouped[pos] ?? []
      grouped[pos].push(p)
    }
    return grouped
  }, [data])

  const fullXDomain = useMemo<Domain>(() => {
    const maxXgXa = data.reduce((m, p) => Math.max(m, p.xg_xa), 0)
    return [0, Math.max(Math.round(maxXgXa * 1.05 * 100) / 100, 1)]
  }, [data])

  const fullYDomain = useMemo<Domain>(() => {
    const maxGA = data.reduce((m, p) => Math.max(m, p.g_a), 0)
    return [0, Math.max(Math.round(maxGA * 1.05 * 100) / 100, 1)]
  }, [data])

  const refMax = Math.max(fullXDomain[1], fullYDomain[1])

  // Reset zoom whenever the underlying dataset changes (e.g. season switch).
  useEffect(() => {
    setXDomain(null)
    setYDomain(null)
  }, [data])

  // Pending domain lives in refs, updated synchronously on every wheel tick (cheap).
  // The expensive part — flushing to React state, which re-renders ~1200 points — is
  // throttled to one commit per animation frame so a fast trackpad fling doesn't queue
  // a render per wheel event.
  const pendingXRef = useRef(fullXDomain)
  const pendingYRef = useRef(fullYDomain)
  const fullXDomainRef = useRef(fullXDomain)
  const fullYDomainRef = useRef(fullYDomain)
  const rafRef = useRef<number | null>(null)
  useEffect(() => { fullXDomainRef.current = fullXDomain }, [fullXDomain])
  useEffect(() => { fullYDomainRef.current = fullYDomain }, [fullYDomain])
  useEffect(() => {
    pendingXRef.current = xDomain ?? fullXDomain
    pendingYRef.current = yDomain ?? fullYDomain
  }, [xDomain, yDomain, fullXDomain, fullYDomain])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      const rect = el.getBoundingClientRect()
      const curX = pendingXRef.current
      const curY = pendingYRef.current
      const plotLeft = rect.left + MARGIN.left + Y_AXIS_WIDTH
      const plotRight = rect.right - MARGIN.right
      const plotTop = rect.top + MARGIN.top
      const plotBottom = rect.bottom - MARGIN.bottom
      const fracX = Math.min(1, Math.max(0, (e.clientX - plotLeft) / (plotRight - plotLeft)))
      const fracY = Math.min(1, Math.max(0, 1 - (e.clientY - plotTop) / (plotBottom - plotTop)))

      const dataX = curX[0] + fracX * (curX[1] - curX[0])
      const dataY = curY[0] + fracY * (curY[1] - curY[0])
      const zoomFactor = e.deltaY < 0 ? 0.85 : 1 / 0.85

      const newWidthX = clampWidth((curX[1] - curX[0]) * zoomFactor, fullXDomainRef.current)
      const newWidthY = clampWidth((curY[1] - curY[0]) * zoomFactor, fullYDomainRef.current)

      pendingXRef.current = [dataX - fracX * newWidthX, dataX + (1 - fracX) * newWidthX]
      pendingYRef.current = [dataY - fracY * newWidthY, dataY + (1 - fracY) * newWidthY]

      if (rafRef.current === null) {
        rafRef.current = requestAnimationFrame(() => {
          rafRef.current = null
          setXDomain(pendingXRef.current)
          setYDomain(pendingYRef.current)
        })
      }
    }

    el.addEventListener('wheel', onWheel, { passive: false })
    return () => {
      el.removeEventListener('wheel', onWheel)
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    }
  }, [])

  // Click-and-drag panning, for navigating around once zoomed in. Uses the same
  // pending-ref + rAF-flush pattern as the wheel handler to stay smooth.
  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    let dragStart: {
      x: number; y: number; domainX: Domain; domainY: Domain; plotWidth: number; plotHeight: number
    } | null = null
    let dragged = false

    const onMouseMove = (e: MouseEvent) => {
      if (!dragStart) return
      const dx = e.clientX - dragStart.x
      const dy = e.clientY - dragStart.y
      if (Math.abs(dx) > 3 || Math.abs(dy) > 3) dragged = true

      const deltaDataX = (dx / dragStart.plotWidth) * (dragStart.domainX[1] - dragStart.domainX[0])
      const deltaDataY = (dy / dragStart.plotHeight) * (dragStart.domainY[1] - dragStart.domainY[0])

      pendingXRef.current = clampDomain(
        [dragStart.domainX[0] - deltaDataX, dragStart.domainX[1] - deltaDataX],
        fullXDomainRef.current,
      )
      pendingYRef.current = clampDomain(
        [dragStart.domainY[0] + deltaDataY, dragStart.domainY[1] + deltaDataY],
        fullYDomainRef.current,
      )

      if (rafRef.current === null) {
        rafRef.current = requestAnimationFrame(() => {
          rafRef.current = null
          setXDomain(pendingXRef.current)
          setYDomain(pendingYRef.current)
        })
      }
    }

    const onMouseUp = () => {
      dragStart = null
      el.style.cursor = 'grab'
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }

    const onMouseDown = (e: MouseEvent) => {
      if (e.button !== 0) return
      e.preventDefault() // avoid native text-selection while dragging
      dragged = false
      const rect = el.getBoundingClientRect()
      dragStart = {
        x: e.clientX,
        y: e.clientY,
        domainX: pendingXRef.current,
        domainY: pendingYRef.current,
        plotWidth: rect.width - MARGIN.left - Y_AXIS_WIDTH - MARGIN.right,
        plotHeight: rect.height - MARGIN.top - MARGIN.bottom,
      }
      el.style.cursor = 'grabbing'
      window.addEventListener('mousemove', onMouseMove)
      window.addEventListener('mouseup', onMouseUp)
    }

    // Swallow the click that follows a drag so it doesn't also open a dot's player modal.
    const onClickCapture = (e: MouseEvent) => {
      if (dragged) {
        e.stopPropagation()
        dragged = false
      }
    }

    el.addEventListener('mousedown', onMouseDown)
    el.addEventListener('click', onClickCapture, true)
    return () => {
      el.removeEventListener('mousedown', onMouseDown)
      el.removeEventListener('click', onClickCapture, true)
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [])

  const isZoomed = xDomain !== null || yDomain !== null
  const resetZoom = () => { setXDomain(null); setYDomain(null) }

  return (
    <div className="relative">
      <div ref={containerRef} className="relative h-[72vh] min-h-[480px] max-h-[840px] cursor-grab">
        {isZoomed && (
          <button
            onClick={resetZoom}
            className="absolute top-2 right-2 z-10 px-3 py-1.5 text-xs bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded"
          >
            Reset zoom
          </button>
        )}
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={MARGIN}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="xg_xa" name="xG+xA" type="number"
              domain={xDomain ?? fullXDomain} allowDataOverflow
              tickFormatter={(v: number) => String(Number(v.toFixed(2)))}
              label={{ value: 'xG + xA', position: 'insideBottom', offset: -20, fill: '#9ca3af' }}
              stroke="#6b7280"
            />
            <YAxis
              dataKey="g_a" name="G+A" type="number"
              domain={yDomain ?? fullYDomain} allowDataOverflow width={Y_AXIS_WIDTH}
              tickFormatter={(v: number) => String(Number(v.toFixed(2)))}
              label={{ value: 'Goals + Assists', angle: -90, position: 'insideLeft', offset: 10, fill: '#9ca3af' }}
              stroke="#6b7280"
            />
            {/* diagonal y=x: above = underperformer (potential sleeper) */}
            <ReferenceLine
              segment={[{ x: 0, y: 0 }, { x: refMax, y: refMax }]}
              stroke="#4b5563" strokeDasharray="4 4"
            />
            <Tooltip
              cursor={{ strokeDasharray: '3 3' }}
              content={({ payload }) => {
                if (!payload?.length) return null
                const p = payload[0].payload as ScatterPoint
                return (
                  <div className="bg-gray-800 border border-gray-700 p-2 rounded text-sm">
                    <div className="font-medium">{p.name}</div>
                    <div className="text-gray-400">{p.position}</div>
                    <div className="text-gray-400">G+A: {p.g_a} · xG+xA: {p.xg_xa.toFixed(2)}</div>
                  </div>
                )
              }}
            />
            <Legend
              verticalAlign="bottom"
              align="center"
              wrapperStyle={{ position: 'relative', marginTop: 16, display: 'flex', justifyContent: 'center', width: '100%' }}
            />
            {Object.entries(byPosition).map(([pos, points]) => (
              <Scatter
                key={pos}
                name={pos}
                data={points}
                fill={POSITION_COLORS[pos] ?? '#9ca3af'}
                opacity={0.8}
                isAnimationActive={false}
                cursor={onPointClick ? 'pointer' : undefined}
                onClick={onPointClick ? (point) => onPointClick(point as unknown as ScatterPoint) : undefined}
              />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <div className="text-center text-xs text-gray-500 mt-1">Scroll to zoom · drag to pan</div>
    </div>
  )
}
