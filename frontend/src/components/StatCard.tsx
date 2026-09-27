import Card from './Card'
import Skeleton from './Skeleton'

export default function StatCard({
  label,
  value,
  hint,
  loading = false,
  error = false,
}: {
  label: string
  value?: string
  hint?: string
  /** Show a placeholder while the number loads. */
  loading?: boolean
  /** The number could not be loaded. */
  error?: boolean
}) {
  return (
    <Card className="flex flex-col gap-1.5">
      <span className="text-sm font-medium text-gray-500">{label}</span>
      {loading ? (
        <Skeleton className="my-1 h-10 w-28" />
      ) : (
        <span className="text-4xl font-bold tracking-tight text-brand tabular-nums">{error ? '-' : value}</span>
      )}
      {loading ? (
        <Skeleton className="h-4 w-36" />
      ) : (
        (error || hint) && <span className="text-sm text-gray-500">{error ? "Couldn't load" : hint}</span>
      )}
    </Card>
  )
}

/** A responsive row of stat cards. */
export function StatRow({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">{children}</div>
}
