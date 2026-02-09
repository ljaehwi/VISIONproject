import { useMutation, useQuery } from '@tanstack/react-query'

const API_BASE = 'http://localhost:8000'

async function healthSystem() {
  const res = await fetch(`${API_BASE}/health/system`)
  if (!res.ok) throw new Error('health/system failed')
  return res.json()
}

async function healthCamera() {
  const res = await fetch(`${API_BASE}/health/camera`)
  if (!res.ok) throw new Error('health/camera failed')
  return res.json()
}

async function setCameraParams(gain: number, black_level: number) {
  const res = await fetch(`${API_BASE}/camera/parameters`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ gain, black_level })
  })
  if (!res.ok) throw new Error('set parameters failed')
  return res.json()
}

async function captureImage() {
  const res = await fetch(`${API_BASE}/camera/capture`)
  if (!res.ok) throw new Error('camera/capture failed')
  return res.json()
}

export function useHealthChecks() {
  const system = useQuery({ queryKey: ['health', 'system'], queryFn: healthSystem, enabled: false })
  const camera = useQuery({ queryKey: ['health', 'camera'], queryFn: healthCamera, enabled: false })
  return { system, camera }
}

export function useSetCameraParams() {
  return useMutation({ mutationFn: (payload: { gain: number; black_level: number }) => setCameraParams(payload.gain, payload.black_level) })
}

export function useCaptureImage() {
  return useMutation({ mutationFn: captureImage })
}

export function wsUrl() {
  return 'ws://localhost:8000/ws/calibration'
}

export async function fetchDatasetImages(params?: { item?: string; split?: string; defect_type?: string; limit?: number }) {
  const qs = new URLSearchParams()
  if (params?.item) qs.set('item', params.item)
  if (params?.split) qs.set('split', params.split)
  if (params?.defect_type) qs.set('defect_type', params.defect_type)
  if (params?.limit) qs.set('limit', String(params.limit))
  if ((params as any)?.offset) qs.set('offset', String((params as any).offset))
  const url = `${API_BASE}/dataset/images${qs.toString() ? `?${qs.toString()}` : ''}`
  const res = await fetch(url)
  if (!res.ok) throw new Error('dataset/images failed')
  return res.json()
}

export function useDatasetImages(params?: { item?: string; split?: string; defect_type?: string; limit?: number; offset?: number }) {
  return useQuery({ queryKey: ['dataset', params], queryFn: () => fetchDatasetImages(params) })
}

export async function fetchDatasetFilters() {
  const res = await fetch(`${API_BASE}/dataset/filters`)
  if (!res.ok) throw new Error('dataset/filters failed')
  return res.json()
}

export function useDatasetFilters() {
  return useQuery({ queryKey: ['dataset', 'filters'], queryFn: fetchDatasetFilters })
}

export async function saveDatasetImage(payload: {
  dataset_image_id: number
  gain: number
  black_level: number
  is_auto_calibration: boolean
  note?: string
}) {
  const res = await fetch(`${API_BASE}/dataset/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if (!res.ok) throw new Error('dataset/save failed')
  return res.json()
}

export function useSaveDatasetImage() {
  return useMutation({ mutationFn: saveDatasetImage })
}
