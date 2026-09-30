import type { ReactNode } from 'react'

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`bg-slate-900 border border-slate-800 rounded-lg p-6 ${className}`}>{children}</div>
  )
}

export function CardTitle({ children }: { children: ReactNode }) {
  return <h2 className="text-xl font-semibold text-white mb-4">{children}</h2>
}
