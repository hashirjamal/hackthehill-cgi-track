/** Hooks for the reporting API (GET /reports/...) and the classification call. One hook for each endpoint. */
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toastLoading, toastProblem, toastSuccess } from '../lib/notify'
import type {
  AccountHistoryRow,
  AgentResultRow,
  AgentRunResult,
  ContextResult,
  DraftResult,
  BreakdownRow,
  CaseContext,
  CaseRow,
  ClassificationSummaryRow,
  ClusterRow,
  FlowRow,
  ProfileRow,
  RootCauseRow,
  WorklistRow,
} from '../types'
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

// --- Accounts and profiles ----------------------------------------------------------------------

export const useAccountHistory = (params: Params) => useList<AccountHistoryRow>('account-history', params, 'the account history')
export const useAccountsTotal = (filters: Params, label: string) => useTotal('account-history', filters, label)
export const useProfiles = (params: Params) => useList<ProfileRow>('case-profiles', params, 'the case profiles')

// --- Agents and classification results ----------------------------------------------------------

export const useAgentResults = (params: Params, label = 'the AI agent results') => useList<AgentResultRow>('agent-results', params, label)

export interface SummaryPage extends Page<ClassificationSummaryRow> {
  group_by: string[]
}
export const useClassificationSummary = (params: Params, label = 'the classification results') =>
  useQuery({
    queryKey: [REPORTS, 'classifications/summary', params],
    queryFn: ({ signal }) => apiGet<SummaryPage>('/reports/classifications/summary', params, signal),
    placeholderData: keepPreviousData,
    meta: { label },
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

// --- Intake -------------------------------------------------------------------------------------

/** The intake template: a brand-new complaint. No category or priority - Laya decides both. */
export interface IntakeComplaint {
  account_id: string
  text: string
  channel: string
  region: string
  source_system: string
}

export interface IntakeResult {
  complaint_id: string
  category: string
  as_of_date: string
  classification: {
    emergency: boolean
    group: { name: string; confidence: number } | null
    priority: { level: 'P1' | 'P2' | 'P3'; target_days: number; raised_by: string[] }
    routing: { team: string; lane: string }
    flags: { name: string; reason: string }[]
  }
}

const INTAKE_TOAST = 'intake'

/** POST /complaints/intake. Laya classifies it and it lands on the worklist, so every report is refreshed. */
export function useIntake() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (complaint: IntakeComplaint) =>
      apiPost<IntakeResult>('/complaints/intake', complaint, { timeoutMs: CLASSIFY_TIMEOUT_MS }),
    meta: { errorTitle: "Couldn't log the complaint", toastId: INTAKE_TOAST },
    onMutate: () => toastLoading('Classifying the complaint', 'Laya is reading it. This takes a few seconds.', INTAKE_TOAST),
    onSuccess: (r) => {
      toastSuccess(`Logged ${r.complaint_id}`, `${r.classification.priority.level} · ${r.classification.routing.team}`, INTAKE_TOAST)
      void queryClient.invalidateQueries({ queryKey: [REPORTS] })
    },
  })
}

// --- AI agent buttons on a case -----------------------------------------------------------------

const AGENT_TIMEOUT_MS = 5 * 60_000 // a local model reading several tools can take a while

/** One of the two buttons. A run that fails (e.g. AI switched off) is a normal answer with status "failed". */
function useAgentRun<T extends AgentRunResult>(id: string, action: 'context' | 'draft', label: string) {
  const queryClient = useQueryClient()
  const toastId = `agent-${action}-${id}`
  return useMutation({
    mutationFn: () => apiPost<T>(`/complaints/${encodeURIComponent(id)}/${action}`, undefined, { timeoutMs: AGENT_TIMEOUT_MS }),
    meta: { errorTitle: `Couldn't ${label.toLowerCase()}`, toastId },
    onMutate: () => toastLoading(`${label}…`, 'The local AI is reading the case. This can take up to a minute.', toastId),
    onSuccess: (r) => {
      if (r.status === 'succeeded') toastSuccess(`${label}: done`, undefined, toastId)
      else toastProblem(`${label}: no result`, r.error ?? 'The AI did not finish.', toastId)
      void queryClient.invalidateQueries({ queryKey: [REPORTS, 'case', id] })
    },
  })
}

export const useGetContext = (id: string) => useAgentRun<ContextResult>(id, 'context', 'Get context')
export const useGenerateDraft = (id: string) => useAgentRun<DraftResult>(id, 'draft', 'Generate draft')
