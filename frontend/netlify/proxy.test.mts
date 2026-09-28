import { describe, expect, it } from 'vitest'
import { extractInternalPath, matchAllowlist } from './functions/proxy.mts'

const ID = 'a1b2c3d4-e5f6-4789-a012-b3c4d5e6f789'

describe('matchAllowlist', () => {
  it('allows GET on the incidents list', () => {
    expect(matchAllowlist('/internal/incidents', 'GET')).toBe('/internal/incidents')
  })

  it('allows GET on an incident detail with a real UUID', () => {
    expect(matchAllowlist(`/internal/incidents/${ID}`, 'GET')).toBe(
      `/internal/incidents/${ID}`,
    )
  })

  it('allows POST approve with a real UUID', () => {
    expect(matchAllowlist(`/internal/incidents/${ID}/approve`, 'POST')).toBe(
      `/internal/incidents/${ID}/approve`,
    )
  })

  it('allows POST reject with a real UUID', () => {
    expect(matchAllowlist(`/internal/incidents/${ID}/reject`, 'POST')).toBe(
      `/internal/incidents/${ID}/reject`,
    )
  })

  it('rejects the wrong method on the list route', () => {
    expect(matchAllowlist('/internal/incidents', 'POST')).toBeNull()
  })

  it('rejects the wrong method on the detail route', () => {
    expect(matchAllowlist(`/internal/incidents/${ID}`, 'POST')).toBeNull()
  })

  it('rejects GET on approve/reject', () => {
    expect(matchAllowlist(`/internal/incidents/${ID}/approve`, 'GET')).toBeNull()
    expect(matchAllowlist(`/internal/incidents/${ID}/reject`, 'GET')).toBeNull()
  })

  it('rejects a non-UUID id segment', () => {
    expect(matchAllowlist('/internal/incidents/not-a-uuid', 'GET')).toBeNull()
    expect(matchAllowlist('/internal/incidents/not-a-uuid/approve', 'POST')).toBeNull()
  })

  it('rejects an unknown action after a valid UUID', () => {
    expect(matchAllowlist(`/internal/incidents/${ID}/delete`, 'POST')).toBeNull()
  })

  it('rejects an extra trailing path segment', () => {
    expect(matchAllowlist(`/internal/incidents/${ID}/approve/extra`, 'POST')).toBeNull()
  })

  it('rejects entirely unrelated paths', () => {
    expect(matchAllowlist('/internal/failures/inject', 'POST')).toBeNull()
    expect(matchAllowlist('/documents', 'GET')).toBeNull()
    expect(matchAllowlist('/', 'GET')).toBeNull()
  })
})

describe('extractInternalPath', () => {
  it('strips the netlify function prefix (the :splat-rewritten path)', () => {
    expect(extractInternalPath('/.netlify/functions/proxy/internal/incidents')).toBe(
      '/internal/incidents',
    )
  })

  it('strips a plain /api prefix (tolerated in case Netlify passes the original path)', () => {
    expect(extractInternalPath('/api/internal/incidents')).toBe('/internal/incidents')
  })

  it('leaves an already-bare path untouched', () => {
    expect(extractInternalPath('/internal/incidents')).toBe('/internal/incidents')
  })
})
