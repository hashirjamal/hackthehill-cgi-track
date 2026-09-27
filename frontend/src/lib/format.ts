export const num = (n: number) => n.toLocaleString('en-GB')
export const pct = (share: number, digits = 0) => `${(share * 100).toFixed(digits)}%`
export const money = (n: number) => n.toLocaleString('en-GB', { maximumFractionDigits: 0 })
/** 2026-06-16 becomes 16 Jun 2026. */
export const shortDate = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })

/** deadline_risk becomes Deadline risk. */
export const humanize = (snake: string) => {
  const text = snake.replace(/_/g, ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}
