import { toast } from 'sonner'
import { userMessage } from '../api/client'

/** An error toast with a message a person can act on, and an optional Retry. Pass an id to show it once. */
export function toastError(title: string, error: unknown, options: { id?: string | number; retry?: () => void } = {}) {
  return toast.error(title, {
    id: options.id,
    description: userMessage(error),
    duration: 8000,
    action: options.retry ? { label: 'Retry', onClick: options.retry } : undefined,
  })
}

export function toastSuccess(title: string, description?: string, id?: string | number) {
  return toast.success(title, { description, id })
}

/** A message that stays until it is replaced by a success or error toast with the same id. */
export function toastLoading(title: string, description: string | undefined, id: string | number) {
  return toast.loading(title, { description, id, duration: Infinity })
}

export function toastInfo(title: string, description?: string) {
  return toast.info(title, { description })
}

/** An error toast with a message we already have in plain words (not from a failed request). */
export function toastProblem(title: string, description: string, id?: string | number) {
  return toast.error(title, { description, id, duration: 8000 })
}
