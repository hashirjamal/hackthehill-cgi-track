import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { Params } from '../api/client'

const PAGE_SIZES = [5, 10, 25, 50, 100, 200]
const RESERVED = ['page', 'page_size', 'sort']

/**
 * Page, page size, sort and filters, kept in the URL. A filtered view can be shared or bookmarked, and the
 * back button works. Filter names are the API's own parameter names, so `params` goes straight to the API.
 *
 * A page with two tables gives the second a `prefix` (say "c_"), so each keeps its own state in the same URL.
 * The first one lists the other prefixes in `others`, so it leaves those keys alone.
 */
export function useListParams({
  pageSize: defaultPageSize = 10,
  prefix = '',
  others = [],
}: { pageSize?: number; prefix?: string; others?: string[] } = {}) {
  const [search, setSearch] = useSearchParams()

  // Does this URL key belong to this table, and what is its name without the prefix?
  const own = useCallback(
    (key: string) => (prefix ? key.startsWith(prefix) : !others.some((o) => key.startsWith(o))),
    [prefix, others],
  )
  const bare = (key: string) => (prefix ? key.slice(prefix.length) : key)
  const named = (key: string) => prefix + key

  const page = Math.max(1, Number(search.get(named('page'))) || 1)
  const requested = Number(search.get(named('page_size')))
  const pageSize = PAGE_SIZES.includes(requested) ? requested : defaultPageSize
  const sort = search.get(named('sort')) || undefined

  const filters = useMemo(() => {
    const out: Record<string, string> = {}
    search.forEach((value, key) => {
      if (own(key) && !RESERVED.includes(bare(key)) && value !== '') out[bare(key)] = value
    })
    return out
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, own, prefix])

  const update = useCallback(
    (patch: Record<string, string | undefined>, resetPage: boolean) => {
      setSearch(
        (prev) => {
          const next = new URLSearchParams(prev)
          for (const [key, value] of Object.entries(patch)) {
            if (value === undefined || value === '') next.delete(prefix + key)
            else next.set(prefix + key, value)
          }
          if (resetPage) next.delete(prefix + 'page')
          return next
        },
        { replace: true },
      )
    },
    [setSearch, prefix],
  )

  /** Everything the API needs: the filters plus paging and sorting. */
  const params: Params = useMemo(() => ({ ...filters, page, page_size: pageSize, sort }), [filters, page, pageSize, sort])

  return {
    params,
    filters,
    page,
    pageSize,
    sort,
    /** A filter changes what matches, so it goes back to the first page. */
    setFilter: (key: string, value: string | undefined) => update({ [key]: value }, true),
    setToggle: (key: string, on: boolean) => update({ [key]: on ? 'true' : undefined }, true),
    setPage: (p: number) => update({ page: p > 1 ? String(p) : undefined }, false),
    setPageSize: (n: number) => update({ page_size: n === defaultPageSize ? undefined : String(n) }, true),
    setSort: (s: string | undefined) => update({ sort: s }, true),
    /** Several changes as one update. Router updates are not queued, so two calls in a row would lose the first. */
    setMany: (patch: Record<string, string | undefined>) => update(patch, true),
    hasFilters: Object.keys(filters).length > 0,
    /** Clears this table's filters, page and sort, and leaves the other table's alone. */
    clearFilters: () =>
      setSearch(
        (prev) => {
          const next = new URLSearchParams(prev)
          for (const key of [...next.keys()]) if (own(key)) next.delete(key)
          return next
        },
        { replace: true },
      ),
  }
}
