export function Loading({ text = 'Loading...' }: { text?: string }) {
  return <div className="text-slate-400 animate-pulse">{text}</div>
}
