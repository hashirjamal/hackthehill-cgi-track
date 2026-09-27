import { Check, ClipboardCopy, ListChecks, Loader2, PenLine } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useGenerateDraft, useGetContext } from '../api/reports'
import { humanize, shortDate } from '../lib/format'
import type { CaseContext } from '../types'
import Card, { CardTitle } from './Card'
import SystemsChecked from './SystemsChecked'
import { Button } from './Controls'

/** The two AI buttons on a case. Nothing runs until staff click, and nothing is ever sent or changed:
 * "Get context" suggests action items, "Generate draft" writes a reply for staff to edit and send themselves. */
export default function AgentPanel({ data }: { data: CaseContext }) {
  const id = data.case.complaint_id
  const context = useGetContext(id)
  const draft = useGenerateDraft(id)
  const busy = context.isPending || draft.isPending

  // Only the latest "Get context" run: each click is a fresh list, not added to the old one.
  const latestRun = data.action_items.reduce<number | null>((max, a) => (a.run_id !== null && (max === null || a.run_id > max) ? a.run_id : max), null)
  const actions = data.action_items.filter((a) => a.run_id === latestRun)
  const latestDraft = data.drafts[0]
  const trace = (runId: number | null | undefined) => (runId != null ? (data.systems_checked[String(runId)] ?? []) : [])

  const contextError = context.data?.status === 'failed' ? context.data.error : null
  const draftError = draft.data?.status === 'failed' ? draft.data.error : null

  return (
    <Card>
      <CardTitle title="AI assistant" hint="Checks Northwind's systems for you. Runs on our own machine; it suggests, staff decide and act." />
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => context.mutate()} disabled={busy}>
          <span className="inline-flex items-center gap-2">
            {context.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ListChecks className="h-4 w-4" />}
            {context.isPending ? 'Reading the case…' : 'Get context'}
          </span>
        </Button>
        <Button variant="ghost" onClick={() => draft.mutate()} disabled={busy}>
          <span className="inline-flex items-center gap-2">
            {draft.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <PenLine className="h-4 w-4" />}
            {draft.isPending ? 'Writing…' : 'Generate draft'}
          </span>
        </Button>
      </div>

      <section className="mt-5">
        <h3 className="text-xs font-medium tracking-wide text-gray-500 uppercase">Action items</h3>
        {contextError && <p className="mt-2 rounded-xl bg-red-50 p-3 text-sm text-red-700">{contextError}</p>}
        {actions.length === 0 ? (
          <p className="mt-2 text-sm text-gray-500">Click Get context for a ranked list of what to do on this case.</p>
        ) : (
          <ol className="mt-2 flex flex-col gap-2.5">
            {actions.map((a) => (
              <li key={a.action_id} className="flex gap-3 rounded-xl bg-gray-100 p-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand text-xs font-semibold text-white">{a.rank}</span>
                <div className="text-sm">
                  <p className="font-medium text-gray-800">{a.description}</p>
                  {a.rationale && <p className="mt-0.5 text-gray-500">{a.rationale}</p>}
                  <p className="mt-1 text-xs text-gray-400">{humanize(a.action_type)}</p>
                </div>
              </li>
            ))}
          </ol>
        )}
        <SystemsChecked calls={trace(latestRun)} />
      </section>

      <section className="mt-6">
        <h3 className="text-xs font-medium tracking-wide text-gray-500 uppercase">Draft reply</h3>
        {draftError && <p className="mt-2 rounded-xl bg-red-50 p-3 text-sm text-red-700">{draftError}</p>}
        {latestDraft ? (
          <>
            <DraftEditor key={latestDraft.draft_id} body={latestDraft.body} created={latestDraft.created_at} />
            <SystemsChecked calls={trace(latestDraft.run_id)} />
          </>
        ) : (
          <p className="mt-2 text-sm text-gray-500">Click Generate draft for a reply to the customer that you can edit, copy and send yourself.</p>
        )}
      </section>
    </Card>
  )
}

function DraftEditor({ body, created }: { body: string; created: string }) {
  const [text, setText] = useState(body)
  const [copied, setCopied] = useState(false)
  useEffect(() => {
    if (!copied) return
    const t = setTimeout(() => setCopied(false), 2000)
    return () => clearTimeout(t)
  }, [copied])

  const copy = () => {
    void navigator.clipboard.writeText(text).then(() => setCopied(true))
  }

  return (
    <div className="mt-2">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        className="min-h-48 w-full rounded-xl bg-gray-100 p-3 text-sm text-gray-800 focus:ring-2 focus:ring-brand/30 focus:outline-none"
      />
      <div className="mt-2 flex items-center justify-between gap-2">
        <span className="text-xs text-gray-400">Drafted {shortDate(created)}. Not sent: review, edit and send it yourself.</span>
        <Button variant="ghost" onClick={copy}>
          <span className="inline-flex items-center gap-2">
            {copied ? <Check className="h-4 w-4" /> : <ClipboardCopy className="h-4 w-4" />}
            {copied ? 'Copied' : 'Copy'}
          </span>
        </Button>
      </div>
    </div>
  )
}
