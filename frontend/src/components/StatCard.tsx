import Card from './Card'

export default function StatCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card className="flex flex-col gap-1.5">
      <span className="text-sm font-medium text-gray-500">{label}</span>
      <span className="text-4xl font-bold tracking-tight text-brand tabular-nums">{value}</span>
      {hint && <span className="text-sm text-gray-500">{hint}</span>}
    </Card>
  )
}

/** A responsive row of stat cards. */
export function StatRow({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">{children}</div>
}
