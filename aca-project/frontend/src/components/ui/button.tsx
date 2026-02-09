import { ButtonHTMLAttributes } from 'react'

export function Button({ className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={`inline-flex items-center justify-center rounded px-4 py-2 text-sm font-semibold bg-white/10 hover:bg-white/20 ${className}`}
      {...props}
    />
  )
}
