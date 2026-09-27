/** Hooks for the reporting API (GET /reports/...) and the classification call. One hook for each endpoint. */
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toastLoading, toastSuccess } from '../lib/notify'
import type { BreakdownRow, CaseContext, CaseRow, ClusterRow, FlowRow, RootCauseRow, WorklistRow } from '../types'
import { apiGet, apiPost, type Params } from './client'
import type { Page } from './types'

// Every report query starts with this key, so one call refreshes them all after data changes.
export const REPORTS = 'reports'

/** A paged list. The previous page stays on screen while the next one loads. */
function useList<T>(path: string, params: Params, label: string) {
  return useQuery({
    queryKey: [REPORTS, path, params],
    queryFn: ({ signal }) => apiGet<Page<T>>(`/reports/${path}`, params, signal),
    placeholderData: keepPreviousData,
    meta: { label },
  })
}

/** Just the number of rows a filter matches, for stat cards. Asks for one row. */
function useTotal(path: string, filters: Params, label: string) {
  const params = { ...filters, page: 1, page_size: 1 }
  return useQuery({
    queryKey: [REPORTS, path, params],
    queryFn: ({ signal }) => apiGet<Page<unknown>>(`/reports/${path}`, params, signal),
    select: (page) => page.total,
    meta: { label },
  })
}

// --- Worklist -----------------------------------------------------------------------------------

export const useWorklist = (params: Params) => useList<WorklistRow>('worklist', params, 'the worklist')
export const useWorklistTotal = (filters: Params, label: string) => useTotal('worklist', filters, label)

// --- Backlog ------------------------------------------------------------------------------------

export const useBacklogFlow = (params: Params) => useList<FlowRow>('backlog-flow', params, 'the backlog history')

export interface BreakdownPage extends Page<BreakdownRow> {
  group_by: string[]
}
export const useBacklogBreakdown = (params: Params) =>
  useQuery({
    queryKey: [REPORTS, 'backlog-breakdown', params],
    queryFn: ({ signal }) => apiGet<BreakdownPage>('/reports/backlog-breakdown', params, signal),
    placeholderData: keepPreviousData,
    meta: { label: 'the backlog breakdown' },
  })

// --- Root cause ---------------------------------------------------------------------------------

export const useRootCause = (params: Params, label = 'the root-cause figures') => useList<RootCauseRow>('root-cause', params, label)
export const useRootCauseClusters = (params: Params, label = 'the backlog clusters') =>
  useList<ClusterRow>('root-cause/clusters', params, label)

// --- Cases --------------------------------------------------------------------------------------

export const useCases = (params: Params) => useList<CaseRow>('cases', params, 'the cases')

/** One case with its context. A 404 is an answer ("no such complaint"), not something to retry. */
export const useCaseContext = (id: string) =>
  useQuery({
    queryKey: [REPORTS, 'case', id],
    queryFn: ({ signal }) => apiGet<CaseContext>(`/reports/cases/${encodeURIComponent(id)}`, { history_limit: 20 }, signal),
    meta: { label: `case ${id}` },
  })

// --- Classification -----------------------------------------------------------------------------

export interface ClassifyComplaint {
  complaint_id: string
  category: string
  priority: string
  sla_days: number
  channel: string
  region: string
  source_system: string
  date_opened: string
  account_id: string
  transferred_between_systems?: boolean
}

interface ProcessResponse {
  as_of_date: string
  results: { complaint_id: string; group: { source: string } | null; emergency: boolean }[]
}

const CLASSIFY_TOAST = 'classify'
const CLASSIFY_TIMEOUT_MS = 5 * 60_000 // Laya takes a few seconds for each complaint

/** POST /complaints/process. Shows progress, then a summary, and refreshes every report. */
export function useClassify() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (complaints: ClassifyComplaint[]) => apiPost<ProcessResponse>('/complaints/process', { complaints }, { timeoutMs: CLASSIFY_TIMEOUT_MS }),
    meta: { errorTitle: "Couldn't classify the complaints", toastId: CLASSIFY_TOAST },
    onMutate: (complaints) => {
      toastLoading(`Classifying ${complaints.length} ${complaints.length === 1 ? 'complaint' : 'complaints'}`, 'This takes a few seconds for each one.', CLASSIFY_TOAST)
    },
    onSuccess: (response) => {
      const n = response.results.length
      const fromData = response.results.filter((r) => r.group?.source === 'data').length
      const emergencies = response.results.filter((r) => r.emergency).length
      const parts = [`${n - fromData - emergencies} sorted by Laya`, `${fromData} used the data category`]
      if (emergencies) parts.push(`${emergencies} sent to emergency dispatch`)
      toastSuccess(`Classified ${n} ${n === 1 ? 'complaint' : 'complaints'}`, parts.join(' · '), CLASSIFY_TOAST)
      void queryClient.invalidateQueries({ queryKey: [REPORTS] })
    },
  })
}
