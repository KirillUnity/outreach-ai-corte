import axios from 'axios'

export function apiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') {
      return detail
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (typeof item === 'string') {
            return item
          }
          if (item && typeof item === 'object' && 'msg' in item) {
            return String((item as { msg: string }).msg)
          }
          return JSON.stringify(item)
        })
        .join('; ')
    }
    return error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'Request failed'
}
