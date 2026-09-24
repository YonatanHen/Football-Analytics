import { useEffect, useMemo, useRef, useState } from 'react'
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'

export interface PlotPoint {
  id: string
  name: string
  x: number
  y: number
  color: string
  radius: number
  label?: string
  selected?: boolean
}

interface ScatterPlotProps {
  points: PlotPoint[]
  xLabel: string
  yLabel: string
  onPointClick?: (id: string) => void
}

const Y_AXIS_WIDTH = 44
const MARGIN = { top: 24, right: 28, bottom: 40, left: 16 }
const MIN_ZOOM_FRACTION = 0.03 // don't let a single wheel-zoom session collapse past 3% of the full domain
const TICK = { fill: '#56635c', fontSize: 11, fontFamily: 'JetBrains Mono' }

type Domain = [number, number]

function clampWidth(width: number, full: Domain): number {
  const fullWidth = full[1] - full[0]
  return Math.min(fullWidth, Math.max(fullWidth * MIN_ZOOM_FRACTION, width))
}

// Shift a domain window back inside the full data range, preserving its width.
function clampDomain(domain: Domain, full: Domain): Domain {
  const width = domain[1] - domain[0]
  let [lo, hi] = domain
  if (lo < full[0]) { lo = full[0]; hi = lo + width }
  if (hi > full[1]) { hi = full[1]; lo = hi - width }
  return [lo, hi]
}

interface ShapeProps { cx?: number; cy?: number; payload?: PlotPoint }

function PointShape({ cx = 0, cy = 0, payload }: ShapeProps) {
  if (!payload) return null
  return (
    <g>
      {payload.selected && <circle cx={cx} cy={cy} r={payload.radius + 4} fill="none" stroke="#e7ede9" strokeOpacity={0.35} />}
      <circle cx={cx} cy={cy} r={payload.radius} fill={payload.color} />
      {payload.label && (
        <text x={cx + payload.radius + 6} y={cy + 4} fill="#8a978f" fontSize={11} fontFamily="JetBrains Mono">
          {payload.label}
        </text>
      )}
    </g>
  )
}

export default function ScatterPlot({ points, xLabel, yLabel, onPointClick }: ScatterPlotProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [xDomain, setXDomain] = useState<Domain | null>(null)
  const [yDomain, setYDomain] = useState<Domain | null>(null)

  // One shared range for both axes, rounded up to a whole number of ~6 even steps.
  const { full, ticks } = useMemo(() => {
    const max = Math.max(points.reduce((m, p) => Math.max(m, p.x, p.y), 0) * 1.03, 1)
    const raw = max / 6
    const mag = 10 ** Math.floor(Math.log10(raw))
    const step = ([1, 2, 2.5, 5, 10].find((f) => f * mag >= raw) ?? 10) * mag
    const top = Math.ceil(max / step) * step
    return { full: [0, top] as Domain, ticks: Array.from({ length: Math.round(top / step) + 1 }, (_, i) => i * step) }
  }, [points])

  // Reset zoom whenever the axes or the range change, not on every point restyle.
  const top = full[1]
  useEffect(() => {
    setXDomain(null)
    setYDomain(null)
  }, [top, xLabel, yLabel])

  // Wheel ticks update refs; React state is flushed at most once per frame.
  const pendingXRef = useRef(full)
  const pendingYRef = useRef(full)
  const fullRef = useRef(full)
  const rafRef = useRef<number | null>(null)
  useEffect(() => { fullRef.current = full }, [full])
  useEffect(() => {
    pendingXRef.current = xDomain ?? full
    pendingYRef.current = yDomain ?? full
  }, [xDomain, yDomain, full])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const flush = () => {
      if (rafRef.current !== null) return
      rafRef.current = requestAnimationFrame(() => {
        rafRef.current = null
        setXDomain(pendingXRef.current)
        setYDomain(pendingYRef.current)
      })
    }

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
      const zoom = e.deltaY < 0 ? 0.85 : 1 / 0.85
      const wX = clampWidth((curX[1] - curX[0]) * zoom, fullRef.current)
      const wY = clampWidth((curY[1] - curY[0]) * zoom, fullRef.current)
      pendingXRef.current = [dataX - fracX * wX, dataX + (1 - fracX) * wX]
      pendingYRef.current = [dataY - fracY * wY, dataY + (1 - fracY) * wY]
      flush()
    }

    let drag: { x: number; y: number; dX: Domain; dY: Domain; w: number; h: number } | null = null
    let dragged = false

    const onMove = (e: MouseEvent) => {
      if (!drag) return
      const dx = e.clientX - drag.x
      const dy = e.clientY - drag.y
      if (Math.abs(dx) > 3 || Math.abs(dy) > 3) dragged = true
      const shiftX = (dx / drag.w) * (drag.dX[1] - drag.dX[0])
      const shiftY = (dy / drag.h) * (drag.dY[1] - drag.dY[0])
      pendingXRef.current = clampDomain([drag.dX[0] - shiftX, drag.dX[1] - shiftX], fullRef.current)
      pendingYRef.current = clampDomain([drag.dY[0] + shiftY, drag.dY[1] + shiftY], fullRef.current)
      flush()
    }
    const onUp = () => {
      drag = null
      el.style.cursor = 'grab'
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    const onDown = (e: MouseEvent) => {
      if (e.button !== 0) return
      e.preventDefault()
      dragged = false
      const rect = el.getBoundingClientRect()
      drag = {
        x: e.clientX, y: e.clientY, dX: pendingXRef.current, dY: pendingYRef.current,
        w: rect.width - MARGIN.left - Y_AXIS_WIDTH - MARGIN.right,
        h: rect.height - MARGIN.top - MARGIN.bottom,
      }
      el.style.cursor = 'grabbing'
      window.addEventListener('mousemove', onMove)
      window.addEventListener('mouseup', onUp)
    }
    // Swallow the click that ends a drag so it does not also select a point.
    const onClickCapture = (e: MouseEvent) => {
      if (dragged) { e.stopPropagation(); dragged = false }
    }

    el.addEventListener('wheel', onWheel, { passive: false })
    el.addEventListener('mousedown', onDown)
    el.addEventListener('click', onClickCapture, true)
    return () => {
      el.removeEventListener('wheel', onWheel)
      el.removeEventListener('mousedown', onDown)
      el.removeEventListener('click', onClickCapture, true)
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    }
  }, [])

  const isZoomed = xDomain !== null || yDomain !== null
  const fmt = (v: number) => String(Number(v.toFixed(1)))

  return (
    <div ref={containerRef} className="relative h-full w-full cursor-grab">
      {isZoomed && (
        <button
          onClick={() => { setXDomain(null); setYDomain(null) }}
          className="btn-ghost absolute right-4 top-3 z-10 h-7 text-xs"
        >
          Reset zoom
        </button>
      )}
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={MARGIN}>
          <CartesianGrid stroke="#1f2b25" />
          <XAxis
            dataKey="x" type="number" domain={xDomain ?? full} allowDataOverflow
            tickFormatter={fmt} tick={TICK} tickLine={false} axisLine={false} ticks={isZoomed ? undefined : ticks}
            label={{ value: `${xLabel}  (expected)`, position: 'insideBottom', offset: -24, ...TICK, fill: '#8a978f' }}
          />
          <YAxis
            dataKey="y" type="number" domain={yDomain ?? full} allowDataOverflow width={Y_AXIS_WIDTH}
            tickFormatter={fmt} tick={TICK} tickLine={false} axisLine={false} ticks={isZoomed ? undefined : ticks}
            label={{ value: `${yLabel}  (actual)`, angle: -90, position: 'insideLeft', offset: -4, ...TICK, fill: '#8a978f' }}
          />
          <ReferenceLine
            segment={[{ x: 0, y: 0 }, { x: full[1], y: full[1] }]}
            stroke="#1f9360" strokeWidth={1.5} ifOverflow="hidden"
            label={{ value: 'xGI = GI', position: 'insideTopRight', fill: '#1f9360', fontSize: 11, fontFamily: 'JetBrains Mono' }}
          />
          <Tooltip
            cursor={false}
            isAnimationActive={false}
            content={({ payload }) => {
              if (!payload?.length) return null
              const p = payload[0].payload as PlotPoint
              return (
                <div className="rounded-md border border-line-strong bg-surface px-3 py-2 text-xs">
                  <div className="text-ink">{p.name}</div>
                  <div className="mt-0.5 font-mono text-muted">{xLabel} {p.x.toFixed(1)} · {yLabel} {p.y}</div>
                </div>
              )
            }}
          />
          <Scatter
            data={points}
            shape={(props: unknown) => <PointShape {...(props as ShapeProps)} />}
            isAnimationActive={false}
            cursor={onPointClick ? 'pointer' : undefined}
            onClick={onPointClick ? (p) => onPointClick((p as unknown as PlotPoint).id) : undefined}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}
