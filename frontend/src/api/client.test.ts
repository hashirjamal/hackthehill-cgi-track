import { describe, expect, it } from 'vitest'
import { ApiError, buildQuery, isAbort, isRetryable, serverMessage, userMessage } from './client'

describe('buildQuery', () => {
  it('skips empty values and repeats array keys', () => {
    expect(buildQuery({ page: 2, region: ['Ashford', 'Fenwick'], q: '', sort: undefined, breached: false, x: null })).toBe(
      '?page=2&region=Ashford&region=Fenwick&breached=false',
    )
  })
  it('gives an empty string when there is nothing to send', () => {
    expect(buildQuery({})).toBe('')
    expect(buildQuery()).toBe('')
  })
  it('encodes values', () => {
    expect(buildQuery({ category: 'Billing - disputed amount' })).toBe('?category=Billing+-+disputed+amount')
  })
})

describe('serverMessage', () => {
  it('reads a string detail', () => {
    expect(serverMessage({ detail: "complaint 'X' not found" })).toBe("complaint 'X' not found")
  })
  it('reads FastAPI validation errors and drops the query prefix', () => {
    expect(serverMessage({ detail: [{ loc: ['query', 'page_size'], msg: 'Input should be less than or equal to 200' }] })).toBe(
      'page_size: Input should be less than or equal to 200',
    )
  })
  it('gives nothing for other bodies', () => {
    expect(serverMessage(undefined)).toBeUndefined()
    expect(serverMessage({ error: 'x' })).toBeUndefined()
  })
})

describe('userMessage and isRetryable', () => {
  it('explains an unreachable server and allows a retry', () => {
    const e = new ApiError('network', 'Network error')
    expect(userMessage(e)).toMatch(/Can't reach the server/)
    expect(isRetryable(e)).toBe(true)
  })
  it('shows the server message for a bad request, and does not retry it', () => {
    const e = new ApiError('http', 'HTTP 422', 422, 'cannot sort by password')
    expect(userMessage(e)).toBe('cannot sort by password')
    expect(isRetryable(e)).toBe(false)
  })
  it('hides server internals for a 500 but retries it', () => {
    const e = new ApiError('http', 'HTTP 500', 500, 'Traceback ...')
    expect(userMessage(e)).not.toMatch(/Traceback/)
    expect(isRetryable(e)).toBe(true)
  })
  it('handles a 404 and cancelled requests', () => {
    expect(userMessage(new ApiError('http', 'HTTP 404', 404, "complaint 'A' not found"))).toBe("complaint 'A' not found")
    expect(isAbort(new ApiError('aborted', 'Cancelled'))).toBe(true)
    expect(isRetryable(new ApiError('aborted', 'Cancelled'))).toBe(false)
  })
  it('copes with an unknown error', () => {
    expect(userMessage(new Error('boom'))).toBe('Something went wrong. Please try again.')
  })
})
