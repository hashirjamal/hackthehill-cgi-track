import { num } from '../lib/format'

/** A plain bar chart in CSS. Hover a bar to see its value. */
export default function BarChart({
  data,
  height = 176,
}: {
  data: { label: string; value: number }[]
  height?: number
}) {
  const max = Math.max(...data.map((d) => d.value), 1)
  return (
    <div>
      <div className="flex items-end gap-1.5" style={{ height }}>
        {data.map((d) => (
          <div
            key={d.label}
            title={`${d.label}: ${num(d.value)}`}
            className="flex-1 rounded-t-lg bg-brand/75 transition-colors hover:bg-brand"
            style={{ height: `${Math.max((d.value / max) * 100, 2)}%` }}
          />
        ))}
      </div>
      <div className="mt-2 flex justify-between text-xs text-gray-500">
        <span>{data[0]?.label}</span>
        <span>{data[data.length - 1]?.label}</span>
      </div>
    </div>
  )
}

/** A horizontal bar with a label and a share, for splits such as how cases ended. */
export function ShareBar({ label, share }: { label: string; share: number }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span className="text-gray-700">{label}</span>
        <span className="text-gray-500 tabular-nums">{(share * 100).toFixed(0)}%</span>
      </div>
      <div className="h-2 rounded-full bg-gray-100">
        <div className="h-2 rounded-full bg-brand/75" style={{ width: `${share * 100}%` }} />
      </div>
    </div>
  )
}
