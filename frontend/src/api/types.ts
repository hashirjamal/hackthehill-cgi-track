/** The envelope every list endpoint returns. */
export interface Page<T> {
  items: T[]
  page: number
  page_size: number
  total: number
  total_pages: number
  sort: string[]
}
