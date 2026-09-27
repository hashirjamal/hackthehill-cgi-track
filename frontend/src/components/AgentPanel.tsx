import { Bot, Check, ClipboardCopy, ListChecks, Loader2, PenLine, Workflow } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useGenerateDraft, useGetContext } from '../api/reports'
import { cn } from '../lib/cn'
import { shortDate } from '../lib/format'
import type { CaseContext } from '../types'
import Card, { CardTitle } from './Card'
import { Button } from './Controls'
import SystemsChecked from './SystemsChecked'

type Mode = 'ai' | 'rules'
const MODE_KEY = 'case-assistant-mode'

function savedMode(): Mode {
  try {
    return localStorage.getItem(MODE_KEY) === 'rules' ? 'rules' : 'ai'
  } catch {
    return 'ai'
  }
}

/** The two buttons on a case. Nothing runs until staff click, and nothing is ever sent or changed.
 * Both check the source systems. With AI on, a local LLM reads the records and writes the result;
 * with AI off, fixed rules and templates do - same systems, same trace, no AI anywhere. */
export default function AgentPanel({ data }: { data: CaseContext }) {
  const id = data.case.complaint_id
  const context = useGetContext(id)
  const draft = useGenerateDraft(id)
  const busy = context.isPending || draft.isPending
  const [mode, setMode] = useState<Mode>(savedMode)

  const chooseMode = (m: Mode) => {
    setMode(m)
    try {
      localStorage.setItem(MODE_KEY, m)
    } catch {
      /* the choice just isn't remembered */
    }
  }

  // Only the latest "Get context" run: each click is a fresh list, not added to the old one.
  const latestRun = data.action_items.reduce<number | null>((max, a) => (a.run_id !== null && (max === null || a.run_id > max) ? a.run_id : max), null)
  const actions = data.action_items.filter((a) => a.run_id === latestRun)
  const latestDraft = data.drafts[0]
  const trace = (runId: number | null | undefined) => (runId != null ? (data.systems_checked[String(runId)] ?? []) : [])
  const madeBy = (runId: number | null | undefined) => (runId != null ? data.run_modes[String(runId)] : undefined)

  return (
    <Card>
      <CardTitle
        title="Work this case"
        hint="Pulls the records from billing, CRM, case and call systems. It suggests; you decide and act."
        action={<ModeSwitch mode={mode} onChange={chooseMode} disabled={busy} />}
      />
      <div className="flex flex-wrap gap-2 border-b border-line pb-4">
        <Button onClick={() => context.mutate(mode)} disabled={busy}>
          <span className="inline-flex items-center gap-2">
            {context.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ListChecks className="h-4 w-4" />}
            {context.isPending ? 'Checking the systems…' : 'Get context'}
          </span>
        </Button>
        <Button variant="ghost" onClick={() => draft.mutate(mode)} disabled={busy}>
          <span className="inline-flex items-center gap-2">
            {draft.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <PenLine className="h-4 w-4" />}
            {draft.isPending ? 'Writing…' : 'Generate draft'}
          </span>
        </Button>
      </div>

      <section className="mt-5">
        <SectionTitle title="Action items" mode={madeBy(latestRun)} />
        {context.data?.error && <Note text={context.data.error} />}
        {actions.length === 0 ? (
          <p className="mt-2 text-sm text-gray-500">Click Get context for a ranked list of what to do on this case.</p>
        ) : (
          <ol className="mt-1 flex flex-col">
            {actions.map((a) => (
              <li key={a.action_id} className="flex gap-3 border-b border-line/70 py-2.5 last:border-0">
                <span className="num flex h-6 w-6 shrink-0 items-center justify-center rounded-sm border border-line bg-page text-xs text-gray-600">{a.rank}</span>
                <div className="text-sm">
                  <p className="font-medium text-gray-800">{a.description}</p>
                  {a.rationale && <p className="mt-0.5 text-gray-500">{a.rationale}</p>}
                  <p className="mt-1 font-mono text-[11px] text-gray-400">{a.action_type}</p>
                </div>
              </li>
            ))}
          </ol>
        )}
        <SystemsChecked calls={trace(latestRun)} />
      </section>

      <section className="mt-6">
        <SectionTitle title="Draft reply" mode={madeBy(latestDraft?.run_id)} />
        {draft.data?.error && <Note text={draft.data.error} />}
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

function ModeSwitch({ mode, onChange, disabled }: { mode: Mode; onChange: (m: Mode) => void; disabled: boolean }) {
  const option = (m: Mode, label: string, Icon: typeof Bot) => (
    <button
      type="button"
      aria-pressed={mode === m}
      disabled={disabled}
      onClick={() => onChange(m)}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-sm transition-colors focus:outline-none disabled:opacity-50',
        mode === m ? 'bg-card font-medium text-brand-dark shadow-sm ring-1 ring-line' : 'text-gray-500 hover:text-gray-700',
      )}
    >
      <Icon className="h-4 w-4" />
      {label}
    </button>
  )
  return (
    <div className="flex shrink-0 gap-1 rounded-md border border-line bg-page p-0.5" title="With AI off, the same systems are checked and fixed rules write the result.">
      {option('ai', 'AI on', Bot)}
      {option('rules', 'AI off', Workflow)}
    </div>
  )
}

function SectionTitle({ title, mode }: { title: string; mode: 'ai' | 'rules' | undefined }) {
  return (
    <div className="flex items-center gap-2">
      <h3 className="text-[11px] font-medium tracking-wider text-gray-500 uppercase">{title}</h3>
      {mode && (
        <span className={cn('rounded-sm px-1.5 py-0.5 text-[11px] font-medium', mode === 'ai' ? 'bg-brand-soft text-brand' : 'bg-gray-200 text-gray-600')}>
          {mode === 'ai' ? 'Written by local AI' : 'Built by rules - no AI'}
        </span>
      )}
    </div>
  )
}

function Note({ text }: { text: string }) {
  return <p className="mt-2 rounded-md border border-amber-200 bg-amber-50 p-2.5 text-sm text-amber-900">{text}</p>
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
        className="min-h-56 w-full rounded-md border border-line bg-page p-3 text-sm leading-relaxed text-ink focus:ring-2 focus:ring-brand/30 focus:outline-none"
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
