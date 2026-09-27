import type { ServerTable } from '../components/DataTable'
import type { useListParams } from '../hooks/useListParams'

/** What a paged query gives the table: the page envelope, and the loading and error state. */
interface PagedQuery {
  data?: { page: number; page_size: number; total: number; total_pages: number }
  isPending: boolean
  isFetching: boolean
  error: unknown
  refetch: () => unknown
}

/** Connect a table to its URL state (`list`) and its query, so paging, sorting and loading all follow the API. */
export function serverTable(list: ReturnType<typeof useListParams>, query: PagedQuery, emptyText?: string): ServerTable {
  return {
    // The numbers of the rows on screen, which are the previous page's while the next one loads.
    page: query.data?.page ?? list.page,
    pageSize: query.data?.page_size ?? list.pageSize,
    total: query.data?.total ?? 0,
    totalPages: query.data?.total_pages ?? 1,
    sort: list.sort,
    onPageChange: list.setPage,
    onPageSizeChange: list.setPageSize,
    onSortChange: list.setSort,
    isLoading: query.isPending,
    isFetching: query.isFetching,
    error: query.error,
    onRetry: () => void query.refetch(),
    onClearFilters: list.hasFilters ? list.clearFilters : undefined,
    emptyText,
  }
}
