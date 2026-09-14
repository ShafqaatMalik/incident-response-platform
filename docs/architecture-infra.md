# Live infrastructure

The FastAPI backend runs continuously on Cloud Run, backed by Supabase
Postgres and Google Secret Manager. Three background Cloud Run Jobs —
synthetic traffic, a daily cleanup, and a twice-daily failure-injection
trigger — are fired by Cloud Scheduler and generate real, ongoing
activity against the live service. A Netlify-hosted dashboard reads and
approves/rejects incidents over CORS-permitted HTTPS, and the four AI
agents call Anthropic's API directly from the backend, with every call
traced to Google Cloud Trace via OpenTelemetry.

```mermaid
flowchart TD
    NETLIFY["Netlify<br/>Incident dashboard (static React)"]

    subgraph GCP["Google Cloud — australia-southeast1"]
        direction TB
        SCHEDULER["Cloud Scheduler"]
        TRAFFIC["Cloud Run Job: irp-synthetic-traffic<br/>*/7 * * * *<br/>SA: irp-synthetic-traffic-sa"]
        TRIGGER["Cloud Run Job: irp-failure-injection-trigger<br/>06:43 and 18:43 UTC<br/>SA: irp-synthetic-traffic-sa"]
        CLEANUP["Cloud Run Job: irp-synthetic-cleanup<br/>03:17 UTC daily<br/>SA: irp-synthetic-cleanup-sa"]
        SERVICE["Cloud Run Service<br/>incident-response-platform (FastAPI)"]
        SECRETS[("Secret Manager<br/>api-key, database-url, anthropic-api-key")]
        TRACE["Cloud Trace"]

        SCHEDULER --> TRAFFIC
        SCHEDULER --> TRIGGER
        SCHEDULER --> CLEANUP

        TRAFFIC -->|POST /documents| SERVICE
        TRIGGER -->|"POST /internal/failures/inject + 5 pipeline-stage calls"| SERVICE

        SECRETS -.->|api-key| TRAFFIC
        SECRETS -.->|api-key| TRIGGER
        SECRETS -.->|database-url| CLEANUP
        SECRETS -.->|"api-key, database-url, anthropic-api-key"| SERVICE

        SERVICE -->|OpenTelemetry spans| TRACE
    end

    NETLIFY -->|HTTPS, CORS-permitted| SERVICE

    DB[("Supabase Postgres<br/>via Transaction Pooler")]
    ANTHROPIC["Anthropic API"]

    SERVICE -->|reads/writes| DB
    CLEANUP -->|"direct asyncpg connection, deletes old synthetic rows"| DB
    SERVICE -->|"4 agents' calls: Triage/Investigation/Diagnosis/Remediation"| ANTHROPIC

    classDef compute fill:#e0e7ff,stroke:#4f46e5,stroke-width:1px,color:#1e1b4b
    classDef data fill:#dbeafe,stroke:#2563eb,stroke-width:1px,color:#1e3a8a
    classDef secrets fill:#fef3c7,stroke:#d97706,stroke-width:1px,color:#78350f
    classDef external fill:#f3f4f6,stroke:#6b7280,stroke-width:1px,color:#111827
    classDef observability fill:#dcfce7,stroke:#16a34a,stroke-width:1px,color:#14532d

    class SERVICE,TRAFFIC,TRIGGER,CLEANUP,SCHEDULER compute
    class DB data
    class SECRETS secrets
    class NETLIFY,ANTHROPIC external
    class TRACE observability
```

**Reading the diagram**: dashed arrows are Secret Manager grants, not
traffic. `irp-synthetic-traffic-sa` is deliberately **reused** by both
`irp-synthetic-traffic` and `irp-failure-injection-trigger` — both only
ever make HTTP calls to the public API with an API key, an identical
capability shape. `irp-synthetic-cleanup` gets its own service account
(`irp-synthetic-cleanup-sa`) because it needs a materially more
sensitive capability instead: a direct database connection, bypassing
the API entirely (see `STATUS.md`, 2026-09-07). The dashboard never
talks to the database, Secret Manager, or Anthropic directly — every
path runs through the one FastAPI service.
