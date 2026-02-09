import { useCallback, useRef, useState } from 'react'
import type { CalibrationStep } from '../types'
import { wsUrl } from './useApi'

export function useCalibrationSocket() {
  const [steps, setSteps] = useState<CalibrationStep[]>([])
  const [status, setStatus] = useState<'idle' | 'running' | 'done'>('idle')
  const socketRef = useRef<WebSocket | null>(null)

  const connect = useCallback((payload: { target_gv: number; tolerance: number; max_iterations: number }) => {
    if (socketRef.current) {
      socketRef.current.close()
    }
    setSteps([])
    setStatus('running')

    const ws = new WebSocket(wsUrl())
    socketRef.current = ws

    ws.onopen = () => {
      ws.send(JSON.stringify(payload))
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data) as CalibrationStep
      setSteps((prev) => [...prev, data])
      if (data.status === 'CONVERGED' || data.status === 'FAILED') {
        setStatus('done')
        ws.close()
      }
    }

    ws.onerror = () => {
      setStatus('done')
    }
  }, [])

  return { steps, status, connect }
}
