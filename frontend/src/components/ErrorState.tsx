import { AlertCircle, RotateCw } from 'lucide-react'
import { ApiError, isRetryable, userMessage } from '../api/client'
import { Button } from './Controls'

/** Shown where the data should be when it could not be loaded. */
export default function ErrorState({
  title = "Couldn't load this",
  error,
  onRetry,
  children,
}: {
  title?: string
  error: unknown
  onRetry?: () => void
  /** Replaces the default "change the filters" hint when a retry would not help, for example a link back. */
  children?: React.ReactNode
}) {
  const status = error instanceof ApiError && error.status ? `HTTP ${error.status}` : null
  return (
    <div role="alert" className="flex flex-col items-center gap-3 px-4 py-12 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-50 text-red-600">
        <AlertCircle className="h-6 w-6" />
      </div>
      <div>
        <p className="text-base font-semibold text-gray-900">{title}</p>
        <p className="mx-auto mt-1 max-w-md text-sm text-gray-600">{userMessage(error)}</p>
        {status && <p className="mt-1 text-xs text-gray-400">{status}</p>}
      </div>
      {onRetry && isRetryable(error) ? (
        <Button onClick={onRetry}>
          <span className="inline-flex items-center gap-2">
            <RotateCw className="h-4 w-4" /> Try again
          </span>
        </Button>
      ) : (
        (children ?? <p className="text-sm text-gray-500">Change the filters or the sort above and it will load again.</p>)
      )}
    </div>
  )
}
