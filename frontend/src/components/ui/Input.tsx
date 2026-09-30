import type { InputHTMLAttributes } from 'react'

export function Input({ className = '', ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...rest}
      className={`w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 ${className}`}
    />
  )
}
