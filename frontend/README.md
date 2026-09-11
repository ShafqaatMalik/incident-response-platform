# Incident Response Dashboard

A viewer + approve/reject tool for the incident pipeline. Two screens: an
incident list and an incident detail page. Talks directly to the FastAPI
backend at `http://localhost:8000` — see `ARCHITECTURE.md` §3/§17 and
`STATUS.md` for the full design/rationale.

## Setup

```bash
npm install
```

Create `.env.local` (gitignored — Vite ignores any `*.local` file by
default) with:

```
VITE_API_KEY=<same value as the root .env's API_KEY>
VITE_API_BASE_URL=http://localhost:8000
```

`VITE_API_BASE_URL` is optional — it defaults to `http://localhost:8000`.

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
