/** A small fetch wrapper for the FastAPI backend: query strings, timeouts and readable errors. */

export type ParamValue = string | number | boolean | null | undefined | (string | number)[]
export type Params = Record<string, ParamValue>

// In development Vite forwards /api to the backend. Set VITE_API_URL to call a server directly.
const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? '/api'
const TIMEOUT_MS = 30_000 // reads; a slow call such as classification passes its own
export type ApiErrorKind = 'network' | 'timeout' | 'http' | 'aborted'

export class ApiError extends Error {
  kind: ApiErrorKind
  status: number | null
  /** What the server said, when it said anything useful. */
  serverMessage: string | undefined

  constructor(kind: ApiErrorKind, message: string, status: number | null = null, serverMessage?: string) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.status = status
    this.serverMessage = serverMessage
  }
}

/** Turn params into `?a=1&b=x&b=y`. Empty values are skipped, arrays repeat the key. */
export function buildQuery(params: Params = {}): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    if (Array.isArray(value)) value.forEach((v) => search.append(key, String(v)))
    else search.append(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

/** Pull a readable message out of a FastAPI error body (`detail` is a string or a list of validation errors). */
export function serverMessage(body: unknown): string | undefined {
  if (!body || typeof body !== 'object') return undefined
  const detail = (body as { detail?: unknown }).detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const parts = detail.map((d) => {
      if (!d || typeof d !== 'object') return String(d)
      const { loc, msg } = d as { loc?: unknown[]; msg?: string }
      const where = Array.isArray(loc) ? loc.filter((x) => x !== 'query' && x !== 'body' && x !== 'path').join('.') : ''
      return where ? `${where}: ${msg}` : (msg ?? '')
    })
    return parts.filter(Boolean).join('; ') || undefined
  }
  return undefined
}

/** A message a person can act on. Server details are shown for mistakes in the request, not for server faults. */
export function userMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return 'Something went wrong. Please try again.'
  switch (error.kind) {
    case 'network':
      return "Can't reach the server. Check that the API is running, then try again."
    case 'timeout':
      return 'The server took too long to answer. Try again in a moment.'
    case 'aborted':
      return 'The request was cancelled.'
  }
  const status = error.status ?? 0
  if (status === 404) return error.serverMessage ?? 'That could not be found.'
  if (status === 400 || status === 422) return error.serverMessage ?? 'The request was not valid.'
  if (status === 401 || status === 403) return "You don't have access to this."
  if (status === 503) return 'The service is not available right now. Try again in a moment.'
  if (status >= 500) return 'The server ran into a problem. Try again in a moment.'
  return error.serverMessage ?? `The request failed (${status}).`
}

/** Worth trying again: the server was unreachable or had a fault. A wrong request will fail the same way again. */
export function isRetryable(error: unknown): boolean {
  if (!(error instanceof ApiError)) return false
  return error.kind === 'network' || error.kind === 'timeout' || (error.status !== null && error.status >= 500)
}

export function isAbort(error: unknown): boolean {
  return error instanceof ApiError && error.kind === 'aborted'
}

interface RequestOptions {
  params?: Params
  body?: unknown
  signal?: AbortSignal
  timeoutMs?: number
}

export async function apiRequest<T>(method: 'GET' | 'POST', path: string, options: RequestOptions = {}): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(new DOMException('timeout', 'TimeoutError')), options.timeoutMs ?? TIMEOUT_MS)
  options.signal?.addEventListener('abort', () => controller.abort(options.signal?.reason))

  try {
    const response = await fetch(`${BASE}${path}${buildQuery(options.params)}`, {
      method,
      headers: { Accept: 'application/json', ...(options.body !== undefined && { 'Content-Type': 'application/json' }) },
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: controller.signal,
    })

    if (!response.ok) {
      let body: unknown
      try {
        body = await response.json()
      } catch {
        body = undefined // an HTML error page from a proxy, for example
      }
      throw new ApiError('http', `HTTP ${response.status}`, response.status, serverMessage(body))
    }
    return (await response.json()) as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (controller.signal.aborted) {
      const timedOut = controller.signal.reason instanceof DOMException && controller.signal.reason.name === 'TimeoutError'
      throw new ApiError(timedOut ? 'timeout' : 'aborted', timedOut ? 'Timed out' : 'Cancelled')
    }
    throw new ApiError('network', 'Network error')
  } finally {
    clearTimeout(timer)
  }
}

export const apiGet = <T>(path: string, params?: Params, signal?: AbortSignal) => apiRequest<T>('GET', path, { params, signal })
export const apiPost = <T>(path: string, body: unknown, options: { signal?: AbortSignal; timeoutMs?: number } = {}) =>
  apiRequest<T>('POST', path, { body, ...options })
