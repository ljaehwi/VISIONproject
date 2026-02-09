import { useEffect, useMemo, useRef, useState } from 'react'
import { Card } from './components/ui/card'
import { Button } from './components/ui/button'
import { useCalibrationSocket } from './hooks/useCalibrationSocket'
import {
  useCaptureImage,
  useDatasetFilters,
  useDatasetImages,
  useHealthChecks,
  useSaveDatasetImage,
  useSetCameraParams
} from './hooks/useApi'
import type { CalibrationStep, DatasetFilters, DatasetImageItem } from './types'

function LineChart({ steps, target }: { steps: CalibrationStep[]; target: number }) {
  const width = 360
  const height = 160
  const values = steps.map((s) => s.current_gv)
  const max = Math.max(target + 10, ...values, 180)
  const min = Math.min(target - 10, ...values, 40)
  const points = values
    .map((v, i) => {
      const x = (i / Math.max(1, values.length - 1)) * width
      const y = height - ((v - min) / (max - min)) * height
      return `${x},${y}`
    })
    .join(' ')

  const targetY = height - ((target - min) / (max - min)) * height

  return (
    <svg width={width} height={height} className="bg-panel rounded">
      <line x1={0} x2={width} y1={targetY} y2={targetY} stroke="#10b981" strokeDasharray="4 4" />
      <polyline fill="none" stroke="#f59e0b" strokeWidth={2} points={points} />
    </svg>
  )
}

function Viewer({
  imageUrl,
  applyAdjust,
  gain,
  blackLevel
}: {
  imageUrl: string | null
  applyAdjust: boolean
  gain: number
  blackLevel: number
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [img, setImg] = useState<HTMLImageElement | null>(null)
  const [imgData, setImgData] = useState<ImageData | null>(null)
  const [adjustedData, setAdjustedData] = useState<ImageData | null>(null)
  const offscreenRef = useRef<HTMLCanvasElement | null>(null)
  const [scale, setScale] = useState(1)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [dragging, setDragging] = useState(false)
  const [lastPos, setLastPos] = useState({ x: 0, y: 0 })
  const [hover, setHover] = useState<{ x: number; y: number; gv: number; r: number; g: number; b: number } | null>(
    null
  )

  useEffect(() => {
    if (!imageUrl) return
    const image = new Image()
    image.crossOrigin = 'anonymous'
    image.src = imageUrl
    image.onload = () => {
      setImg(image)
      const off = document.createElement('canvas')
      off.width = image.width
      off.height = image.height
      const ctx = off.getContext('2d')
      if (ctx) {
        try {
          ctx.drawImage(image, 0, 0)
          setImgData(ctx.getImageData(0, 0, image.width, image.height))
        } catch {
          setImgData(null)
        }
      }
      setScale(1)
      setOffset({ x: 0, y: 0 })
    }
  }, [imageUrl])

  useEffect(() => {
    if (!imgData) {
      setAdjustedData(null)
      return
    }
    if (!applyAdjust) {
      setAdjustedData(null)
      return
    }
    const data = new Uint8ClampedArray(imgData.data)
    const gainFactor = 1.0 + gain / 24.0
    for (let i = 0; i < data.length; i += 4) {
      const r = Math.min(255, Math.max(0, data[i] * gainFactor + blackLevel))
      const g = Math.min(255, Math.max(0, data[i + 1] * gainFactor + blackLevel))
      const b = Math.min(255, Math.max(0, data[i + 2] * gainFactor + blackLevel))
      data[i] = r
      data[i + 1] = g
      data[i + 2] = b
    }
    setAdjustedData(new ImageData(data, imgData.width, imgData.height))
  }, [imgData, applyAdjust, gain, blackLevel])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !img) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.setTransform(1, 0, 0, 1, 0, 0)
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.setTransform(scale, 0, 0, scale, offset.x, offset.y)
    if (adjustedData) {
      if (!offscreenRef.current) {
        offscreenRef.current = document.createElement('canvas')
      }
      const off = offscreenRef.current
      off.width = adjustedData.width
      off.height = adjustedData.height
      const offCtx = off.getContext('2d')
      if (offCtx) {
        offCtx.putImageData(adjustedData, 0, 0)
        ctx.drawImage(off, 0, 0)
      }
    } else {
      ctx.drawImage(img, 0, 0)
    }
  }, [img, adjustedData, scale, offset])

  useEffect(() => {
    const canvas = canvasRef.current
    const container = containerRef.current
    if (!canvas || !container) return
    const resize = () => {
      canvas.width = container.clientWidth
      canvas.height = container.clientHeight
    }
    resize()
    window.addEventListener('resize', resize)
    return () => window.removeEventListener('resize', resize)
  }, [])

  const onWheel: React.WheelEventHandler<HTMLCanvasElement> = (e) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -0.1 : 0.1
    const nextScale = Math.min(4, Math.max(0.5, scale + delta))
    setScale(nextScale)
  }

  const onMouseDown: React.MouseEventHandler<HTMLCanvasElement> = (e) => {
    setDragging(true)
    setLastPos({ x: e.clientX, y: e.clientY })
  }

  const onMouseUp = () => setDragging(false)

  const onMouseMove: React.MouseEventHandler<HTMLCanvasElement> = (e) => {
    if (dragging) {
      const dx = e.clientX - lastPos.x
      const dy = e.clientY - lastPos.y
      setOffset((o) => ({ x: o.x + dx, y: o.y + dy }))
      setLastPos({ x: e.clientX, y: e.clientY })
    }

    const canvas = canvasRef.current
    const activeData = adjustedData ?? imgData
    if (!canvas || !activeData) return
    const rect = canvas.getBoundingClientRect()
    const x = (e.clientX - rect.left - offset.x) / scale
    const y = (e.clientY - rect.top - offset.y) / scale

    if (x >= 0 && y >= 0 && x < activeData.width && y < activeData.height) {
      const idx = (Math.floor(y) * activeData.width + Math.floor(x)) * 4
      const r = activeData.data[idx]
      const g = activeData.data[idx + 1]
      const b = activeData.data[idx + 2]
      const gv = Math.round((r + g + b) / 3)
      setHover({ x: Math.floor(x), y: Math.floor(y), gv, r, g, b })
    } else {
      setHover(null)
    }
  }

  return (
    <div ref={containerRef} className="bg-black/40 rounded flex items-center justify-center h-full relative">
      <canvas
        ref={canvasRef}
        className="border border-white/10 w-full h-full"
        onWheel={onWheel}
        onMouseDown={onMouseDown}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
        onMouseMove={onMouseMove}
      />
      {!imageUrl && <div className="text-white/50 absolute">No image yet</div>}
      {hover && (
        <div className="absolute bottom-2 right-2 text-xs bg-black/70 px-2 py-1 rounded">
          <div>
            ({hover.x}, {hover.y})
          </div>
          <div>GV: {hover.gv}</div>
          <div>
            RGB: {hover.r}, {hover.g}, {hover.b}
          </div>
        </div>
      )}
    </div>
  )
}

type Rect = { x: number; y: number; w: number; h: number }
const LAYOUT_KEY = 'aca_layout_v1'

function loadLayout(): { controls: Rect; viewer: Rect; right: Rect } | null {
  try {
    const raw = localStorage.getItem(LAYOUT_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed?.controls || !parsed?.viewer || !parsed?.right) return null
    return parsed
  } catch {
    return null
  }
}

function saveLayout(controls: Rect, viewer: Rect, right: Rect) {
  const payload = { controls, viewer, right }
  localStorage.setItem(LAYOUT_KEY, JSON.stringify(payload))
}

function DraggableResizable({
  title,
  rect,
  onChange,
  enabled,
  children
}: {
  title: string
  rect: Rect
  onChange: (next: Rect) => void
  enabled: boolean
  children: React.ReactNode
}) {
  const dragging = useRef(false)
  const resizing = useRef(false)
  const start = useRef({ x: 0, y: 0, rect })

  const onMouseDown: React.MouseEventHandler<HTMLDivElement> = (e) => {
    if (!enabled) return
    dragging.current = true
    start.current = { x: e.clientX, y: e.clientY, rect }
  }

  const onResizeDown: React.MouseEventHandler<HTMLDivElement> = (e) => {
    if (!enabled) return
    e.stopPropagation()
    resizing.current = true
    start.current = { x: e.clientX, y: e.clientY, rect }
  }

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!enabled) return
      if (dragging.current) {
        const dx = e.clientX - start.current.x
        const dy = e.clientY - start.current.y
        onChange({
          ...start.current.rect,
          x: start.current.rect.x + dx,
          y: start.current.rect.y + dy
        })
      } else if (resizing.current) {
        const dx = e.clientX - start.current.x
        const dy = e.clientY - start.current.y
        onChange({
          ...start.current.rect,
          w: Math.max(240, start.current.rect.w + dx),
          h: Math.max(220, start.current.rect.h + dy)
        })
      }
    }

    const onUp = () => {
      dragging.current = false
      resizing.current = false
    }

    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [enabled, onChange])

  return (
    <div className={`absolute ${enabled ? 'ring-1 ring-emerald-500/40' : ''}`} style={{ left: rect.x, top: rect.y, width: rect.w, height: rect.h }}>
      <div
        className={`text-xs uppercase tracking-widest text-white/60 px-3 py-2 select-none ${enabled ? 'cursor-move' : ''}`}
        onMouseDown={onMouseDown}
      >
        {title}
      </div>
      <div className="h-[calc(100%-32px)] px-3 pb-3">
        {children}
      </div>
      {enabled && (
        <div
          onMouseDown={onResizeDown}
          className="absolute right-2 bottom-2 w-3 h-3 bg-emerald-400 rounded-sm cursor-nwse-resize"
        />
      )}
    </div>
  )
}

function App() {
  const [gain, setGain] = useState(8)
  const [blackLevel, setBlackLevel] = useState(10)
  const [targetGv, setTargetGv] = useState(140)
  const [tolerance, setTolerance] = useState(2)
  const [maxIterations, setMaxIterations] = useState(20)
  const [banner, setBanner] = useState<string | null>(null)
  const [datasetPreviewUrl, setDatasetPreviewUrl] = useState<string | null>(null)
  const [manualImageUrl, setManualImageUrl] = useState<string | null>(null)
  const [selectedDatasetId, setSelectedDatasetId] = useState<number | null>(null)
  const [isAutoCalibration, setIsAutoCalibration] = useState(false)
  const [note, setNote] = useState('')
  const [filterItem, setFilterItem] = useState('')
  const [filterSplit, setFilterSplit] = useState('')
  const [filterDefect, setFilterDefect] = useState('')
  const [limit, setLimit] = useState(50)
  const [offset, setOffset] = useState(0)
  const [layoutEdit, setLayoutEdit] = useState(false)
  const [controlsRect, setControlsRect] = useState<Rect>({ x: 24, y: 16, w: 280, h: 640 })
  const [viewerRect, setViewerRect] = useState<Rect>({ x: 320, y: 16, w: 860, h: 640 })
  const [rightRect, setRightRect] = useState<Rect>({ x: 1200, y: 16, w: 320, h: 640 })

  const { steps, status, connect } = useCalibrationSocket()
  const latest = steps[steps.length - 1]
  const liveUrl = latest?.image_url ? `http://localhost:8000${latest.image_url}` : null
  const imageUrl = datasetPreviewUrl ?? manualImageUrl ?? liveUrl

  const logsRef = useRef<HTMLDivElement | null>(null)

  const logLines = useMemo(
    () =>
      steps.map(
        (s) =>
          `#${s.step} gv=${s.current_gv.toFixed(2)} gain=${s.applied_gain.toFixed(2)} black=${s.applied_black_level} ${s.status}`
      ),
    [steps]
  )

  useEffect(() => {
    if (logsRef.current) {
      logsRef.current.scrollTop = logsRef.current.scrollHeight
    }
  }, [logLines])

  useEffect(() => {
    const loaded = loadLayout()
    if (loaded) {
      setControlsRect(loaded.controls)
      setViewerRect(loaded.viewer)
      setRightRect(loaded.right)
    }
  }, [])

  useEffect(() => {
    saveLayout(controlsRect, viewerRect, rightRect)
  }, [controlsRect, viewerRect, rightRect])

  const { system, camera } = useHealthChecks()
  const setParams = useSetCameraParams()
  const capture = useCaptureImage()
  const saveDataset = useSaveDatasetImage()
  const dataset = useDatasetImages({
    limit,
    offset,
    item: filterItem || undefined,
    split: filterSplit || undefined,
    defect_type: filterDefect || undefined
  })
  const filters = useDatasetFilters()

  const onStart = async () => {
    setBanner(null)
    try {
      await system.refetch()
      await camera.refetch()
    } catch (e) {
      setBanner('Health check failed. Backend or DB is not ready.')
      return
    }
    connect({ target_gv: targetGv, tolerance, max_iterations: maxIterations })
  }

  const onSetParams = async () => {
    try {
      await setParams.mutateAsync({ gain, black_level: blackLevel })
    } catch (e) {
      setBanner('Failed to set camera parameters.')
    }
  }

  const onCapture = async () => {
    setBanner(null)
    try {
      const res = await capture.mutateAsync()
      if (res?.image_url) {
        setManualImageUrl(`http://localhost:8000${res.image_url}?t=${Date.now()}`)
      }
    } catch (e) {
      setBanner('Failed to capture image.')
    }
  }

  // Auto-update image when gain/black level changes (debounced)
  const autoUpdateRef = useRef<number | null>(null)
  useEffect(() => {
    if (status === 'running') return
    if (datasetPreviewUrl) {
      setDatasetPreviewUrl(null)
    }
    if (autoUpdateRef.current) {
      window.clearTimeout(autoUpdateRef.current)
    }
    autoUpdateRef.current = window.setTimeout(async () => {
      try {
        await setParams.mutateAsync({ gain, black_level: blackLevel })
        const res = await capture.mutateAsync()
        if (res?.image_url) {
          setManualImageUrl(`http://localhost:8000${res.image_url}?t=${Date.now()}`)
        }
      } catch {
        // ignore transient errors during rapid slider changes
      }
    }, 250)
    return () => {
      if (autoUpdateRef.current) {
        window.clearTimeout(autoUpdateRef.current)
      }
    }
  }, [gain, blackLevel, status, datasetPreviewUrl])

  const onPickDataset = (item: DatasetImageItem) => {
    setSelectedDatasetId(item.id)
    setDatasetPreviewUrl(`http://localhost:8000${item.file_url}?t=${Date.now()}`)
  }

  const onClearDataset = () => setDatasetPreviewUrl(null)

  const onReloadDataset = () => {
    dataset.refetch()
    filters.refetch()
  }

  return (
    <div className="min-h-screen bg-[#0b0d11] text-white">
      <header className="flex items-center justify-between px-6 py-4 border-b border-white/10">
        <div className="text-lg font-semibold">ACA: Auto-Calibration Agent</div>
        <div className="flex gap-3 text-sm">
          <span className="px-2 py-1 rounded bg-emerald-900/40">Camera Online</span>
          <span className="px-2 py-1 rounded bg-emerald-900/40">Vision Ready</span>
        </div>
      </header>

      {banner && (
        <div className="mx-6 my-4 rounded bg-red-500/20 border border-red-500/40 px-4 py-2 text-sm">{banner}</div>
      )}

      <div className="px-6 pb-6">
        <div className="flex justify-end mt-4">
          <Button onClick={() => setLayoutEdit((v) => !v)} className="bg-white/10">
            {layoutEdit ? 'Done' : 'Edit Layout'}
          </Button>
        </div>

        <div className="relative mt-4 h-[calc(100vh-160px)]">
          <DraggableResizable title="Controls" rect={controlsRect} onChange={setControlsRect} enabled={layoutEdit}>
            <div className="space-y-4">
              <div>
                <label className="text-sm">Gain</label>
                <input
                  type="range"
                  min={0}
                  max={24}
                  step={0.1}
                  value={gain}
                  disabled={status === 'running'}
                  onChange={(e) => setGain(parseFloat(e.target.value))}
                  className="w-full"
                />
                <div className="text-xs text-white/60">{gain.toFixed(2)}</div>
              </div>
              <div>
                <label className="text-sm">Black Level</label>
                <input
                  type="range"
                  min={0}
                  max={255}
                  step={1}
                  value={blackLevel}
                  disabled={status === 'running'}
                  onChange={(e) => setBlackLevel(parseInt(e.target.value, 10))}
                  className="w-full"
                />
                <div className="text-xs text-white/60">{blackLevel}</div>
              </div>
              <Button onClick={onSetParams} disabled={status === 'running'} className="w-full">
                Apply Manual Params
              </Button>
              <Button onClick={onCapture} disabled={status === 'running'} className="w-full">
                Capture
              </Button>
              <div>
                <label className="text-sm">Target GV</label>
                <input
                  type="number"
                  value={targetGv}
                  onChange={(e) => setTargetGv(parseFloat(e.target.value))}
                  className="w-full bg-black/40 border border-white/10 rounded px-2 py-1"
                />
              </div>
              <div>
                <label className="text-sm">Tolerance</label>
                <input
                  type="number"
                  value={tolerance}
                  onChange={(e) => setTolerance(parseFloat(e.target.value))}
                  className="w-full bg-black/40 border border-white/10 rounded px-2 py-1"
                />
              </div>
              <div>
                <label className="text-sm">Max Iterations</label>
                <input
                  type="number"
                  value={maxIterations}
                  onChange={(e) => setMaxIterations(parseInt(e.target.value, 10))}
                  className="w-full bg-black/40 border border-white/10 rounded px-2 py-1"
                />
              </div>
              <Button onClick={onStart} className="w-full bg-emerald-500 text-black">
                Auto-Calibration Start
              </Button>
            </div>
          </DraggableResizable>

          <DraggableResizable title="Viewer" rect={viewerRect} onChange={setViewerRect} enabled={layoutEdit}>
            <Viewer imageUrl={imageUrl} applyAdjust={!!datasetPreviewUrl} gain={gain} blackLevel={blackLevel} />
            {datasetPreviewUrl && (
              <div className="mt-2 text-xs text-amber-300">
                Dataset preview active. Clear to see live/manual capture.
              </div>
            )}
            {selectedDatasetId && (
              <div className="mt-2 text-xs text-white/70">
                Selected dataset id: {selectedDatasetId}
              </div>
            )}
          </DraggableResizable>

          <DraggableResizable title="Right Panel" rect={rightRect} onChange={setRightRect} enabled={layoutEdit}>
            <div className="space-y-4 h-full overflow-auto pr-1">
              <Card>
                <div className="text-sm uppercase tracking-widest text-white/60">Metrics</div>
                <div className="mt-3">
                  <LineChart steps={steps} target={targetGv} />
                </div>
                <div className="mt-3 text-sm text-white/70">
                  Iteration: {latest?.step ?? 0} / {maxIterations}
                </div>
                <div className="h-2 bg-white/10 rounded mt-2">
                  <div
                    className="h-2 bg-emerald-500 rounded"
                    style={{ width: `${Math.min(100, ((latest?.step ?? 0) / maxIterations) * 100)}%` }}
                  />
                </div>
              </Card>

              <Card className="h-[220px] flex flex-col">
                <div className="text-sm uppercase tracking-widest text-white/60">Logs</div>
                <div ref={logsRef} className="mt-3 text-xs font-mono overflow-auto flex-1">
                  {logLines.length === 0 && <div className="text-white/50">No logs yet</div>}
                  {logLines.map((line, idx) => (
                    <div key={idx}>{line}</div>
                  ))}
                </div>
              </Card>

              <Card className="h-[280px] flex flex-col">
                <div className="text-sm uppercase tracking-widest text-white/60">Dataset</div>
                <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                  <select
                    value={filterItem}
                    onChange={(e) => setFilterItem(e.target.value)}
                    className="bg-black/40 border border-white/10 rounded px-2 py-1"
                  >
                    <option value="">Item</option>
                    {(filters.data as DatasetFilters | undefined)?.items?.map((v) => (
                      <option key={v} value={v}>
                        {v}
                      </option>
                    ))}
                  </select>
                  <select
                    value={filterSplit}
                    onChange={(e) => setFilterSplit(e.target.value)}
                    className="bg-black/40 border border-white/10 rounded px-2 py-1"
                  >
                    <option value="">Split</option>
                    {(filters.data as DatasetFilters | undefined)?.splits?.map((v) => (
                      <option key={v} value={v}>
                        {v}
                      </option>
                    ))}
                  </select>
                  <select
                    value={filterDefect}
                    onChange={(e) => setFilterDefect(e.target.value)}
                    className="bg-black/40 border border-white/10 rounded px-2 py-1"
                  >
                    <option value="">Defect</option>
                    {(filters.data as DatasetFilters | undefined)?.defect_types?.map((v) => (
                      <option key={v} value={v}>
                        {v}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                  <input
                    type="number"
                    value={limit}
                    onChange={(e) => setLimit(parseInt(e.target.value || '50', 10))}
                    className="bg-black/40 border border-white/10 rounded px-2 py-1"
                    placeholder="limit"
                  />
                  <input
                    type="number"
                    value={offset}
                    onChange={(e) => setOffset(parseInt(e.target.value || '0', 10))}
                    className="bg-black/40 border border-white/10 rounded px-2 py-1"
                    placeholder="offset"
                  />
                </div>
                <div className="mt-3 text-xs overflow-auto flex-1 space-y-1">
                  {dataset.isLoading && <div className="text-white/50">Loading...</div>}
                  {dataset.isError && <div className="text-red-400">Failed to load dataset</div>}
                  {!dataset.isLoading && !dataset.isError && (dataset.data as DatasetImageItem[])?.length === 0 && (
                    <div className="text-white/50">No dataset images</div>
                  )}
                  {(dataset.data as DatasetImageItem[] | undefined)?.map((d) => (
                    <button
                      key={d.id}
                      onClick={() => onPickDataset(d)}
                      className="block w-full text-left hover:text-emerald-300"
                    >
                      [{d.item}/{d.split}/{d.defect_type}] #{d.id}{d.is_mask ? ' (mask)' : ''}
                    </button>
                  ))}
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2">
                  <Button onClick={onReloadDataset} className="w-full">
                    Load
                  </Button>
                  <Button onClick={onClearDataset} className="w-full">
                    Clear
                  </Button>
                </div>
              </Card>

              <Card className="h-[180px] flex flex-col">
                <div className="text-sm uppercase tracking-widest text-white/60">Save Adjusted</div>
                <div className="mt-3 text-xs space-y-2">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={isAutoCalibration}
                      onChange={(e) => setIsAutoCalibration(e.target.checked)}
                    />
                    Auto-Calibration result
                  </label>
                  <input
                    type="text"
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    className="w-full bg-black/40 border border-white/10 rounded px-2 py-1"
                    placeholder="note"
                  />
                </div>
                <Button
                  onClick={async () => {
                    if (!selectedDatasetId) {
                      setBanner('Select a dataset image first.')
                      return
                    }
                    try {
                      const res = await saveDataset.mutateAsync({
                        dataset_image_id: selectedDatasetId,
                        gain,
                        black_level: blackLevel,
                        is_auto_calibration: isAutoCalibration,
                        note: note || undefined
                      })
                      if (res?.image_url) {
                        setManualImageUrl(`http://localhost:8000${res.image_url}?t=${Date.now()}`)
                      }
                    } catch {
                      setBanner('Failed to save adjusted image.')
                    }
                  }}
                  className="mt-2 w-full"
                >
                  Save to DB
                </Button>
              </Card>
            </div>
          </DraggableResizable>
        </div>
      </div>
    </div>
  )
}

export default App
