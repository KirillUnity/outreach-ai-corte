import type { ButtonHTMLAttributes, ReactNode } from 'react'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger'
  children: ReactNode
}

export function Button({ variant = 'primary', children, className = '', ...rest }: Props) {
  const styles = {
    primary: 'bg-blue-600 hover:bg-blue-700 text-white',
    secondary: 'bg-slate-700 hover:bg-slate-600 text-white',
    danger: 'bg-red-600 hover:bg-red-700 text-white',
  }
  return (
    <button
      {...rest}
      className={`px-4 py-2 rounded font-medium transition disabled:opacity-50 ${styles[variant]} ${className}`}
    >
      {children}
    </button>
  )
}
