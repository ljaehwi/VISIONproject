import { PropsWithChildren } from 'react'

export function Card({ children, className = '' }: PropsWithChildren<{ className?: string }>) {
  return <div className={`bg-panel rounded p-4 ${className}`}>{children}</div>
}
