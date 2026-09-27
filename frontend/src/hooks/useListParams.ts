import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { Params } from '../api/client'

const PAGE_SIZES = [5, 10, 25, 50, 100, 200]
const RESERVED = ['page', 'page_size', 'sort']

/**
 * Page, page size, sort and filters, kept in the URL. A filtered view can be shared or bookmarked, and the
 * back button works. Filter names are the API's own parameter names, so `params` goes straight to the API.
 */
export function useListParams({ pageSize: defaultPageSize = 10 }: { pageSize?: number } = {}) {
  const [search, setSearch] = useSearchParams()

  const page = Math.max(1, Number(search.get('page')) || 1)
  const requested = Number(search.get('page_size'))
  const pageSize = PAGE_SIZES.includes(requested) ? requested : defaultPageSize
  const sort = search.get('sort') || undefined

  const filters = useMemo(() => {
    const out: Record<string, string> = {}
    search.forEach((value, key) => {
      if (!RESERVED.includes(key) && value !== '') out[key] = value
    })
    return out
  }, [search])

  const update = useCallback(
    (patch: Record<string, string | undefined>, resetPage: boolean) => {
      setSearch(
        (prev) => {
          const next = new URLSearchParams(prev)
          for (const [key, value] of Object.entries(patch)) {
            if (value === undefined || value === '') next.delete(key)
            else next.set(key, value)
          }
          if (resetPage) next.delete('page')
          return next
        },
        { replace: true },
      )
    },
    [setSearch],
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
    hasFilters: Object.keys(filters).length > 0,
    clearFilters: () => setSearch({}, { replace: true }),
  }
}
