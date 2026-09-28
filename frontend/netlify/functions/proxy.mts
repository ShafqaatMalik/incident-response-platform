// Server-side proxy: holds the real backend API key (a plain Node env
// var, never VITE_-prefixed, never shipped to the browser) and forwards
// only a strict allowlist of routes to the Cloud Run backend. Anything
// off the allowlist -- wrong method, wrong path, malformed id -- 404s
// before ever reaching the backend.

import type { Context } from '@netlify/functions'

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const FUNCTION_PATH_PREFIX = '/.netlify/functions/proxy'

// netlify.toml rewrites /api/* -> this function with the sub-path
// carried via :splat, so req.url's pathname is normally
// "/.netlify/functions/proxy/<rest>". Also tolerates seeing the
// original "/api/<rest>" path directly, in case Netlify's actual
// rewrite behavior differs from what's configured -- unverified until
// a real deploy, so this costs nothing to keep both.
export function extractInternalPath(pathname: string): string {
  if (pathname.startsWith(FUNCTION_PATH_PREFIX)) {
    return pathname.slice(FUNCTION_PATH_PREFIX.length) || '/'
  }
  if (pathname.startsWith('/api')) {
    return pathname.slice(4) || '/'
  }
  return pathname
}

// Pure and independently testable: given the internal path (already
// stripped of any function/proxy prefix) and HTTP method, returns the
// exact backend path to forward to, or null if this request isn't on
// the allowlist at all.
export function matchAllowlist(pathname: string, method: string): string | null {
  if (method === 'GET' && pathname === '/internal/incidents') {
    return '/internal/incidents'
  }

  const detail = pathname.match(/^\/internal\/incidents\/([^/]+)$/)
  if (method === 'GET' && detail && UUID_RE.test(detail[1])) {
    return `/internal/incidents/${detail[1]}`
  }

  const action = pathname.match(/^\/internal\/incidents\/([^/]+)\/(approve|reject)$/)
  if (method === 'POST' && action && UUID_RE.test(action[1])) {
    return `/internal/incidents/${action[1]}/${action[2]}`
  }

  return null
}

function notFound(): Response {
  return new Response(JSON.stringify({ error: { code: 'not_found', message: 'Not found.' } }), {
    status: 404,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
  })
}

export default async (req: Request, _context: Context): Promise<Response> => {
  const url = new URL(req.url)
  const internalPath = extractInternalPath(url.pathname)
  const backendPath = matchAllowlist(internalPath, req.method)

  if (backendPath === null) {
    return notFound()
  }

  const backendUrl = new URL(backendPath, process.env.BACKEND_URL)
  if (backendPath === '/internal/incidents') {
    const limit = url.searchParams.get('limit')
    const offset = url.searchParams.get('offset')
    if (limit !== null) backendUrl.searchParams.set('limit', limit)
    if (offset !== null) backendUrl.searchParams.set('offset', offset)
  }

  const isPost = req.method === 'POST'
  const upstream = await fetch(backendUrl.toString(), {
    method: req.method,
    headers: {
      'X-API-Key': process.env.API_KEY ?? '',
      ...(isPost ? { 'Content-Type': 'application/json' } : {}),
    },
    body: isPost ? await req.text() : undefined,
  })

  const body = await upstream.text()
  return new Response(body, {
    status: upstream.status,
    headers: {
      'Content-Type': upstream.headers.get('Content-Type') ?? 'application/json',
      'Cache-Control': 'no-store',
    },
  })
}
