export const num = (n: number) => n.toLocaleString('en-GB')
export const pct = (share: number, digits = 0) => `${(share * 100).toFixed(digits)}%`
export const money = (n: number) => n.toLocaleString('en-GB', { maximumFractionDigits: 0 })
