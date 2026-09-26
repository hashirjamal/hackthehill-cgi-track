import Card from './Card'

export default function StatCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card className="flex flex-col gap-1">
      <span className="text-xs font-medium text-gray-400">{label}</span>
      <span className="text-2xl font-semibold text-purple-600">{value}</span>
      {hint && <span className="text-xs text-gray-400">{hint}</span>}
    </Card>
  )
}

/** A responsive row of stat cards. */
export function StatRow({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">{children}</div>
}
