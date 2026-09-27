/** Pearson correlation of two equal-length series, or null when it is undefined (too few points, or no spread). */
export function correlation(x: number[], y: number[]): number | null {
  const n = Math.min(x.length, y.length)
  if (n < 2) return null
  const mx = x.slice(0, n).reduce((a, b) => a + b, 0) / n
  const my = y.slice(0, n).reduce((a, b) => a + b, 0) / n
  let sxy = 0
  let sxx = 0
  let syy = 0
  for (let i = 0; i < n; i++) {
    sxy += (x[i] - mx) * (y[i] - my)
    sxx += (x[i] - mx) ** 2
    syy += (y[i] - my) ** 2
  }
  return sxx === 0 || syy === 0 ? null : sxy / Math.sqrt(sxx * syy)
}
