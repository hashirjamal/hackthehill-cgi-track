import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'
import { cn } from '../lib/cn'
import { num } from '../lib/format'
import ErrorState from './ErrorState'
import Skeleton from './Skeleton'

export interface Column<T> {
  key: string
  header: string
  /** How to draw the cell. Defaults to the row's value for `key`. */
  cell?: (row: T) => ReactNode
  /** Sorting in the browser: what to sort by. Defaults to the row's value for `key`. Null makes it unsortable. */
  sortValue?: ((row: T) => string | number | boolean | null) | null
  /** Sorting on the server: the API's sort name. Without one the column cannot be sorted. */
  sortKey?: string
  align?: 'left' | 'right'
}

/** Paging, sorting and loading state held by the page, when the API does the paging and sorting. */
export interface ServerTable {
  page: number
  pageSize: number
  total: number
  totalPages: number
  /** The API's sort string, e.g. "days_overdue:desc". Only the first key is shown. */
  sort: string | undefined
  onPageChange: (page: number) => void
  onPageSizeChange: (pageSize: number) => void
  onSortChange: (sort: string | undefined) => void
  /** Nothing to show yet: the first load. */
  isLoading: boolean
  /** Loading again in the background, for example the next page. */
  isFetching: boolean
  error: unknown
  onRetry: () => void
  /** Offered when a filter matches nothing. */
  onClearFilters?: () => void
  /** What to say when there are no rows and no filter is set, for example "Nothing has been classified yet". */
  emptyText?: string
}

const PAGE_SIZES = [5, 10, 25, 50, 100]
const SKELETON_ROWS = 6

/**
 * A table. Give it `server` and the API does the paging and sorting, and it shows loading and error states.
 * Without `server` it pages and sorts the rows it is given in the browser (for pages not connected to the API yet).
 */
export default function DataTable<T>({
  columns,
  rows,
  rowKey,
  pageSize: initialPageSize = 10,
  total,
  server,
}: {
  columns: Column<T>[]
  rows: T[]
  rowKey: (row: T) => string
  pageSize?: number
  /** Browser mode only: the full count when the rows are a sample of it. */
  total?: number
  server?: ServerTable
}) {
  const [clientSort, setClientSort] = useState<{ key: string; dir: 'asc' | 'desc' } | null>(null)
  const [clientPage, setClientPage] = useState(1)
  const [clientPageSize, setClientPageSize] = useState(initialPageSize)

  const value = (col: Column<T>, row: T) =>
    col.sortValue ? col.sortValue(row) : ((row as Record<string, unknown>)[col.key] as string | number | boolean | null)

  const sorted = useMemo(() => {
    if (server || !clientSort) return rows
    const col = columns.find((c) => c.key === clientSort.key)
    if (!col) return rows
    const dir = clientSort.dir === 'asc' ? 1 : -1
    return [...rows].sort((a, b) => {
      const x = value(col, a)
      const y = value(col, b)
      if (x === y) return 0
      if (x === null || x === undefined) return 1 // empty values always last
      if (y === null || y === undefined) return -1
      return (x > y ? 1 : -1) * dir
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, clientSort, columns, server])

  // What is drawn, in either mode.
  const pageSize = server ? server.pageSize : clientPageSize
  const pages = server ? Math.max(1, server.totalPages) : Math.max(1, Math.ceil(rows.length / clientPageSize))
  const current = server ? server.page : Math.min(clientPage, pages)
  const visible = server ? rows : sorted.slice((current - 1) * clientPageSize, current * clientPageSize)
  const shown = server ? server.total : (total ?? rows.length)
  const from = visible.length === 0 ? 0 : (current - 1) * pageSize + 1
  const to = visible.length === 0 ? 0 : (current - 1) * pageSize + visible.length

  // The column that is sorted now, and which way.
  const serverFirst = server?.sort?.split(',')[0]?.split(':')
  const activeKey = server ? serverFirst?.[0] : clientSort?.key
  const activeDir = server ? (serverFirst?.[1] === 'desc' ? 'desc' : 'asc') : clientSort?.dir

  const sortable = (col: Column<T>) => (server ? col.sortKey !== undefined : col.sortValue !== null)
  const isActive = (col: Column<T>) => (server ? col.sortKey !== undefined && col.sortKey === activeKey : col.key === activeKey)

  const toggleSort = (col: Column<T>) => {
    if (!sortable(col)) return
    if (server) {
      const key = col.sortKey!
      // Ascending, then descending, then back to the endpoint's own order.
      if (activeKey !== key) server.onSortChange(`${key}:asc`)
      else server.onSortChange(activeDir === 'asc' ? `${key}:desc` : undefined)
      return
    }
    setClientSort((s) => (s?.key === col.key ? (s.dir === 'asc' ? { key: col.key, dir: 'desc' } : null) : { key: col.key, dir: 'asc' }))
  }

  const goToPage = (p: number) => (server ? server.onPageChange(p) : setClientPage(p))
  const changePageSize = (n: number) => {
    if (server) server.onPageSizeChange(n)
    else {
      setClientPageSize(n)
      setClientPage(1)
    }
  }

  const failed = !!server && !!server.error && rows.length === 0 && !server.isLoading
  const empty = !server?.isLoading && !failed && visible.length === 0

  return (
    <div>
      <div className={cn('overflow-x-auto transition-opacity', server?.isFetching && !server.isLoading && 'opacity-60')} aria-busy={server?.isFetching}>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs font-semibold tracking-wide text-gray-500 uppercase">
              {columns.map((col) => {
                const active = isActive(col)
                return (
                  <th
                    key={col.key}
                    aria-sort={active ? (activeDir === 'asc' ? 'ascending' : 'descending') : undefined}
                    className={cn('px-3 py-2 font-medium whitespace-nowrap', col.align === 'right' ? 'text-right' : 'text-left')}
                  >
                    <button
                      type="button"
                      disabled={!sortable(col)}
                      onClick={() => toggleSort(col)}
                      className={cn('inline-flex items-center gap-1 uppercase focus:outline-none', sortable(col) && 'hover:text-brand', active && 'text-brand')}
                    >
                      {col.header}
                      {active && (activeDir === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                    </button>
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {server?.isLoading &&
              Array.from({ length: SKELETON_ROWS }, (_, i) => (
                <tr key={`skeleton-${i}`} aria-hidden>
                  {columns.map((col) => (
                    <td key={col.key} className="px-3 py-3.5">
                      <Skeleton className={cn('h-5', col.align === 'right' ? 'ml-auto w-10' : i % 2 ? 'w-24' : 'w-32')} />
                    </td>
                  ))}
                </tr>
              ))}

            {!server?.isLoading &&
              visible.map((row) => (
                <tr key={rowKey(row)} className="group">
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={cn(
                        'px-3 py-3.5 whitespace-nowrap text-gray-800 first:rounded-l-xl last:rounded-r-xl group-hover:bg-brand-soft',
                        col.align === 'right' && 'text-right tabular-nums',
                      )}
                    >
                      {col.cell ? col.cell(row) : String((row as Record<string, unknown>)[col.key] ?? '')}
                    </td>
                  ))}
                </tr>
              ))}
          </tbody>
        </table>

        {failed && server && <ErrorState error={server.error} onRetry={server.onRetry} />}
        {empty && (
          <div className="flex flex-col items-center gap-2 px-3 py-12 text-center">
            <p className="text-base font-medium text-gray-700">
              {server?.onClearFilters || !server?.emptyText ? 'Nothing matches these filters' : server.emptyText}
            </p>
            {server?.onClearFilters && (
              <button type="button" onClick={server.onClearFilters} className="text-sm font-medium text-brand hover:underline">
                Clear filters
              </button>
            )}
          </div>
        )}
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 px-1 text-sm text-gray-500">
        <span className="inline-flex items-center gap-2">
          {server?.isLoading ? (
            <Skeleton className="h-4 w-28" />
          ) : (
            failed ? (
              <span>-</span>
            ) : (
              <>
              {num(from)}–{num(to)} of {num(shown)}
              {!server && shown > rows.length && <span className="text-gray-400"> · sample rows</span>}
              </>
            )
          )}
          {server?.isFetching && !server.isLoading && <Loader2 className="h-4 w-4 animate-spin text-brand" aria-label="Updating" />}
        </span>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2">
            Rows
            <select
              value={pageSize}
              onChange={(e) => changePageSize(Number(e.target.value))}
              className="rounded-lg bg-gray-100 px-2 py-1 text-gray-700 focus:ring-2 focus:ring-brand/30 focus:outline-none"
            >
              {(PAGE_SIZES.includes(pageSize) ? PAGE_SIZES : [...PAGE_SIZES, pageSize].sort((a, b) => a - b)).map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <div className="flex items-center gap-1">
            <button
              type="button"
              aria-label="Previous page"
              disabled={current <= 1}
              onClick={() => goToPage(current - 1)}
              className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 hover:text-brand disabled:opacity-30 disabled:hover:bg-transparent"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="px-1 tabular-nums">
              {current} / {pages}
            </span>
            <button
              type="button"
              aria-label="Next page"
              disabled={current >= pages}
              onClick={() => goToPage(current + 1)}
              className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 hover:text-brand disabled:opacity-30 disabled:hover:bg-transparent"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
