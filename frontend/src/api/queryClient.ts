import { MutationCache, QueryCache, QueryClient } from '@tanstack/react-query'
import { toastError } from '../lib/notify'
import { isAbort, isRetryable } from './client'

// Give a query `meta: { label: 'the worklist' }` and a failed load says "Couldn't load the worklist".
declare module '@tanstack/react-query' {
  interface Register {
    queryMeta: { label?: string }
    mutationMeta: { errorTitle?: string; toastId?: string }
  }
}

export const queryClient: QueryClient = new QueryClient({
  queryCache: new QueryCache({
    // Runs once a load has failed for good, after any retries. Failures that share a label (the four stat cards,
    // say) become one toast, and Retry reloads all of them.
    onError: (error, query) => {
      if (isAbort(error)) return
      const label = query.meta?.label
      toastError(`Couldn't load ${label ?? 'the data'}`, error, {
        id: label ?? query.queryHash,
        // Only offered when trying again could work. A request the server rejected fails the same way again.
        retry: isRetryable(error)
          ? () =>
              void queryClient.invalidateQueries(
                label
                  ? { predicate: (q) => q.meta?.label === label && q.state.status === 'error' }
                  : { queryKey: query.queryKey, exact: true },
              )
          : undefined,
      })
    },
  }),
  mutationCache: new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      if (isAbort(error)) return
      toastError(mutation.meta?.errorTitle ?? 'That did not work', error, { id: mutation.meta?.toastId })
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      // Retry when the server was unreachable or faulted. A rejected request (422, 404) would fail the same way.
      retry: (failureCount, error) => failureCount < 2 && isRetryable(error),
    },
  },
})
