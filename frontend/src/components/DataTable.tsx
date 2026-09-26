import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight } from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'
import { cn } from '../lib/cn'
import { num } from '../lib/format'

export interface Column<T> {
  key: string
  header: string
  /** How to draw the cell. Defaults to the row's value for `key`. */
  cell?: (row: T) => ReactNode
  /** What to sort by. Defaults to the row's value for `key`. Set to null to make the column unsortable. */
  sortValue?: ((row: T) => string | number | boolean | null) | null
  align?: 'left' | 'right'
}

const PAGE_SIZES = [5, 10, 25]

/**
 * A table with sorting and paging in the browser, over the rows it is given.
 * When the pages move to the API, sorting and paging move to the server and this takes them as props.
 */
export default function DataTable<T>({
  columns,
  rows,
  rowKey,
  pageSize: initialPageSize = 10,
  total,
}: {
  columns: Column<T>[]
  rows: T[]
  rowKey: (row: T) => string
  pageSize?: number
  /** The full count when the rows are only a sample of it. */
  total?: number
}) {
  const [sort, setSort] = useState<{ key: string; dir: 'asc' | 'desc' } | null>(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(initialPageSize)

  const value = (col: Column<T>, row: T) =>
    col.sortValue ? col.sortValue(row) : ((row as Record<string, unknown>)[col.key] as string | number | boolean | null)

  const sorted = useMemo(() => {
    if (!sort) return rows
    const col = columns.find((c) => c.key === sort.key)
    if (!col) return rows
    const dir = sort.dir === 'asc' ? 1 : -1
    return [...rows].sort((a, b) => {
      const x = value(col, a)
      const y = value(col, b)
      if (x === y) return 0
      if (x === null || x === undefined) return 1 // empty values always last
      if (y === null || y === undefined) return -1
      return (x > y ? 1 : -1) * dir
    })
  }, [rows, sort, columns])

  const shown = total ?? rows.length
  const pages = Math.max(1, Math.ceil(rows.length / pageSize))
  const current = Math.min(page, pages)
  const visible = sorted.slice((current - 1) * pageSize, current * pageSize)
  const from = rows.length === 0 ? 0 : (current - 1) * pageSize + 1
  const to = Math.min(current * pageSize, rows.length)

  const toggleSort = (col: Column<T>) => {
    if (col.sortValue === null) return
    setSort((s) => (s?.key === col.key ? (s.dir === 'asc' ? { key: col.key, dir: 'desc' } : null) : { key: col.key, dir: 'asc' }))
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs font-semibold tracking-wide text-gray-500 uppercase">
              {columns.map((col) => {
                const sortable = col.sortValue !== null
                const active = sort?.key === col.key
                return (
                  <th key={col.key} className={cn('px-3 py-2 font-medium whitespace-nowrap', col.align === 'right' ? 'text-right' : 'text-left')}>
                    <button
                      type="button"
                      disabled={!sortable}
                      onClick={() => toggleSort(col)}
                      className={cn(
                        'inline-flex items-center gap-1 uppercase focus:outline-none',
                        sortable && 'hover:text-brand',
                        active && 'text-brand',
                      )}
                    >
                      {col.header}
                      {active && (sort.dir === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                    </button>
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
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
            {visible.length === 0 && (
              <tr>
                <td colSpan={columns.length} className="px-3 py-10 text-center text-gray-400">
                  Nothing matches these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 px-1 text-xs text-gray-500">
        <span>
          {from}–{to} of {num(shown)}
          {shown > rows.length && <span className="text-gray-400"> · sample rows</span>}
        </span>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2">
            Rows
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value))
                setPage(1)
              }}
              className="rounded-lg bg-gray-100 px-2 py-1 text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand/30"
            >
              {PAGE_SIZES.map((s) => (
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
              onClick={() => setPage(current - 1)}
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
              onClick={() => setPage(current + 1)}
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
