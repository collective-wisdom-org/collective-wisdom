import { test } from 'node:test'
import assert from 'node:assert/strict'
import { clock } from './format.ts'

test('clock: local 12-hour time with am/pm', () => {
  const cases: [number, number, string][] = [
    [0, 0, '12:00 am'],
    [0, 30, '12:30 am'],
    [9, 5, '9:05 am'],
    [12, 0, '12:00 pm'],
    [23, 59, '11:59 pm'],
  ]
  for (const [h, m, want] of cases) assert.equal(clock(new Date(2026, 0, 2, h, m).getTime()), want)
})
