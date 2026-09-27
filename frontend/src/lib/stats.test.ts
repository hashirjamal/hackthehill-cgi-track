import { describe, expect, it } from 'vitest'
import { correlation } from './stats'

describe('correlation', () => {
  it('is 1 for a perfect rise and -1 for a perfect fall', () => {
    expect(correlation([1, 2, 3, 4], [2, 4, 6, 8])).toBeCloseTo(1)
    expect(correlation([1, 2, 3, 4], [8, 6, 4, 2])).toBeCloseTo(-1)
  })
  it('is null when it cannot be worked out', () => {
    expect(correlation([1], [1])).toBeNull()
    expect(correlation([1, 1, 1], [1, 2, 3])).toBeNull()
    expect(correlation([], [])).toBeNull()
  })
})
