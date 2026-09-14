# Incident lifecycle

An incident moves through a fixed state machine, not free-form agent chat:
each of the four AI agents owns exactly one transition, a non-AI Validator
checks the proposed action before anything reaches a human, and a human
always makes the final approve/reject call — nothing risky ever executes
without that explicit decision. Any AI stage can escalate straight to a
human instead of guessing; once a human is asked, the outcome is always a
decision, never an escalation.

```mermaid
flowchart TD
    DETECTED([DETECTED])
    TRIAGED([TRIAGED])
    INVESTIGATING([INVESTIGATING])
    DIAGNOSED([DIAGNOSED])
    VALIDATING([VALIDATING])
    VALIDATOR{{"Validator<br/>code rule check, no LLM call"}}
    ESCALATED[[ESCALATED]]

    subgraph HUMAN["HUMAN DECISION — nothing risky executes without this"]
        AWAITING_APPROVAL([AWAITING_APPROVAL])
        APPROVED[[APPROVED]]
        REJECTED[[REJECTED]]
    end

    DETECTED -->|Triage Agent| TRIAGED
    TRIAGED -->|Investigation Agent| INVESTIGATING
    INVESTIGATING -->|Diagnosis Agent| DIAGNOSED
    DIAGNOSED -->|Remediation Agent proposes action| VALIDATING
    VALIDATING --> VALIDATOR
    VALIDATOR -->|evidence-supported, permitted, structurally valid| AWAITING_APPROVAL

    AWAITING_APPROVAL -->|human approves| APPROVED
    AWAITING_APPROVAL -->|human rejects, reason required| REJECTED

    DETECTED -.->|escalate| ESCALATED
    TRIAGED -.->|escalate| ESCALATED
    INVESTIGATING -.->|escalate| ESCALATED
    DIAGNOSED -.->|escalate| ESCALATED
    VALIDATING -.->|escalate| ESCALATED

    classDef agentStage fill:#e0e7ff,stroke:#4f46e5,stroke-width:1px,color:#1e1b4b
    classDef validator fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef terminal fill:#f3f4f6,stroke:#6b7280,stroke-width:1px,color:#111827
    classDef escalated fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#7f1d1d
    classDef human fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#14532d

    class DETECTED,TRIAGED,INVESTIGATING,DIAGNOSED,VALIDATING agentStage
    class VALIDATOR validator
    class ESCALATED escalated
    class AWAITING_APPROVAL,APPROVED,REJECTED human

    style HUMAN fill:#f0fdf4,stroke:#16a34a,stroke-width:3px
```

**Reading the diagram**: indigo boxes are single-call, structured-output
LLM agents (`app/agents/`, each Pydantic-validated, never a raw string
consumed downstream). The amber hexagon is deliberately not styled like
an agent — it's a fixed set of code rules (`app/policies/validation_policy.py`),
not a model call. The green-bordered box is the one part of this system a
human, not an AI, controls — every dashed red arrow is a legitimate,
tested outcome (timeout, invalid output, low confidence), not a failure
of the system.
