export type CalibrationStatus = 'ADJUSTING' | 'CONVERGED' | 'FAILED'

export interface CalibrationStep {
  step: number
  current_gv: number
  target_gv: number
  applied_gain: number
  applied_black_level: number
  status: CalibrationStatus
  message: string
  image_url: string
  raw_image_id: number | null
  inspection_id: number | null
}

export interface CaptureResponse {
  image_url: string
  metadata: {
    gain: number
    black_level: number
    gv_mean: number
    timestamp: string
    raw_image_id: number
  }
}

export interface DatasetImageItem {
  id: number
  item: string
  split: string
  defect_type: string
  file_url: string
  is_mask: boolean
}

export interface DatasetFilters {
  items: string[]
  splits: string[]
  defect_types: string[]
}
