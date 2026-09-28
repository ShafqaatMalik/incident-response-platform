# Incident Response Dashboard

A viewer + approve/reject tool for the incident pipeline. Two screens: an
incident list and an incident detail page. Talks to the FastAPI backend
through a server-side proxy — the browser never holds an API key, in
dev or in production. See `ARCHITECTURE.md` §3/§17 and `STATUS.md` for
the full design/rationale.

## Setup

```bash
npm install
```

Create `.env.local` (gitignored — Vite ignores any `*.local` file by
default) with:

```
API_KEY=<same value as the root .env's API_KEY>
BACKEND_URL=http://localhost:8000
```

Deliberately **not** `VITE_`-prefixed — these are read by
`vite.config.ts` itself (a Node process) to configure the dev server's
proxy, never bundled into browser-shipped code. `BACKEND_URL` is
optional — it defaults to `http://localhost:8000`.

The frontend's own code only ever calls relative `/api/...` paths;
`npm run dev`'s Vite proxy forwards those to `BACKEND_URL` with the key
attached server-side, the same shape the production Netlify Function
uses against the live backend (see `netlify/functions/proxy.mts`).

## Run

With the backend running (`docker compose up -d` from the repo root):

```bash
npm run dev
```

## Build / type-check

```bash
npm run build
```

Runs `tsc -b` (type-check) then `vite build`.

## Test

```bash
npm run test
```

Runs the Netlify Function's allowlist/path-matching tests (Vitest).
