import type { UseQueryResult } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { cn } from '../lib/cn'
import ErrorState from './ErrorState'

/**
 * Draws a query's three states for a block that is not a table: `skeleton` while it loads, an error with a
 * retry if it failed, and `children(data)` once there is data. Stale data stays visible while a reload runs.
 */
export default function QueryState<T>({
  query,
  skeleton,
  children,
}: {
  query: UseQueryResult<T, Error>
  skeleton: ReactNode
  children: (data: T) => ReactNode
}) {
  if (query.isPending) return <>{skeleton}</>
  if (query.isError && query.data === undefined) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />
  return <div className={cn('transition-opacity', query.isFetching && 'opacity-60')}>{children(query.data as T)}</div>
}
