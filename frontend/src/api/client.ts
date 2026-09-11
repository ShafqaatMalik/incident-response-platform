import type { ApiErrorBody, Incident, IncidentListResponse } from '../types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const API_KEY = import.meta.env.VITE_API_KEY ?? ''

export class ApiError extends Error {
  status: number
  code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

// Thrown when the request never reached the server at all (backend down,
// wrong URL, offline) -- distinct from ApiError, which means the server
// responded with an error status.
export class NetworkError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: {
        'X-API-Key': API_KEY,
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...init?.headers,
      },
    })
  } catch (cause) {
    throw new NetworkError(`Could not reach the API at ${BASE_URL}.`, { cause })
  }

  if (!response.ok) {
    let body: ApiErrorBody | null = null
    try {
      body = (await response.json()) as ApiErrorBody
    } catch {
      // response body wasn't JSON -- fall through to the generic message below
    }
    throw new ApiError(
      response.status,
      body?.error.code ?? 'unknown_error',
      body?.error.message ?? `Request failed with status ${response.status}.`,
    )
  }

  return (await response.json()) as T
}

export function listIncidents(limit = 20, offset = 0): Promise<IncidentListResponse> {
  return request<IncidentListResponse>(`/internal/incidents?limit=${limit}&offset=${offset}`)
}

const LIST_ALL_PAGE_SIZE = 100

// Fetches every incident, not just the first page. The list endpoint is
// paginated (max 100/request); grouping incidents into sections client-side
// needs the *complete* set, not just the most recent `limit` -- with more
// than one page of incidents (already true in this DB), a single default
// fetch would silently hide older awaiting-approval incidents from the one
// section where completeness actually matters.
export async function listAllIncidents(): Promise<Incident[]> {
  const first = await listIncidents(LIST_ALL_PAGE_SIZE, 0)
  const items = [...first.items]
  let offset = items.length
  while (offset < first.total) {
    const page = await listIncidents(LIST_ALL_PAGE_SIZE, offset)
    items.push(...page.items)
    offset += page.items.length
    if (page.items.length === 0) break // safety net against an infinite loop
  }
  return items
}

export function getIncident(id: string): Promise<Incident> {
  return request<Incident>(`/internal/incidents/${id}`)
}

export function approveIncident(id: string, approvedBy: string): Promise<Incident> {
  return request<Incident>(`/internal/incidents/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify({ approved_by: approvedBy }),
  })
}

export function rejectIncident(
  id: string,
  rejectedBy: string,
  rejectionReason: string,
): Promise<Incident> {
  return request<Incident>(`/internal/incidents/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify({ rejected_by: rejectedBy, rejection_reason: rejectionReason }),
  })
}

// Human-readable message for any error this client can throw -- the one
// place that decides what a user sees, so list/detail pages don't each
// reinvent this.
export function describeError(err: unknown): string {
  if (err instanceof NetworkError) {
    return `Couldn't reach the API at ${BASE_URL} — is the backend running?`
  }
  if (err instanceof ApiError) {
    if (err.status === 401) {
      return "Invalid API key. Check frontend/.env.local's VITE_API_KEY."
    }
    return err.message
  }
  return 'Something unexpected went wrong.'
}
