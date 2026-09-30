export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="bg-red-900/30 border border-red-700 text-red-200 rounded p-3 text-sm">{message}</div>
  )
}
