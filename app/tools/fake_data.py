"""Shared fake-data source for the app/tools/*.py stubs. Picks one of a
small set of internally-consistent fake scenarios by keyword-matching
the incident's trigger text, so logs/deployments/metrics all tell the
same story instead of each stub inventing unrelated content. See
STATUS.md for why: the previous version of these stubs always returned
identical content regardless of the trigger, which meant every incident
(real or evaluation-harness-generated) got the same fake evidence.

`select_scenario` is a pure function of the trigger string alone — no
shared state, no cache. When app/tools/logs.py, deployments.py, and
metrics.py are all called concurrently (as
investigation_workflow.py does via asyncio.gather) with the same
trigger, each independently computes the same result, so they stay
consistent with each other by construction.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FakeScenario:
    name: str
    log_lines: list[tuple[int, str, str]]  # (minutes_ago, level, message)
    # (minutes_ago, version, description); None = no recent deploy
    deployment: tuple[int, str, str] | None
    error_rate: float
    p99_latency_ms: float
    cpu_utilization: float


_DATABASE_KEYWORDS = (
    "database",
    "postgres",
    "disk",
    "connection pool",
    "replica",
    "deadlock",
    "timeout",
    "dependency service",
    "third-party",
    "upstream",
    "unreachable",
    "connection refused",
)
_DEPLOYMENT_KEYWORDS = (
    "deploy",
    "rollout",
    "rolled out",
    "release",
    "version",
    "rollback",
    "pipeline",
    "build",
)
_AUTH_KEYWORDS = (
    "auth",
    "login",
    "password",
    "certificate",
    "token",
    "credential",
    "identity provider",
    "session",
)
_LATENCY_KEYWORDS = ("latency", "slow", "p99", "performance", "degraded")

_SCENARIOS: dict[str, FakeScenario] = {
    "database": FakeScenario(
        name="database",
        log_lines=[
            (2, "ERROR", "connection pool exhausted, 0 available connections"),
            (3, "ERROR", "query timeout after 5000ms against primary database"),
            (6, "WARN", "disk utilization on database volume at 91%"),
            (12, "INFO", "database read replica lag increasing"),
        ],
        deployment=None,
        error_rate=0.35,
        p99_latency_ms=3800.0,
        cpu_utilization=0.55,
    ),
    "deployment": FakeScenario(
        name="deployment",
        log_lines=[
            (1, "ERROR", "new revision failing readiness probe"),
            (2, "ERROR", "rollout stalled: 2 of 10 replicas healthy"),
            (3, "WARN", "elevated 5xx rate immediately following deploy"),
            (8, "INFO", "deployment rollout started"),
        ],
        deployment=(8, "v2.7.0", "new revision rolled out, health checks failing"),
        error_rate=0.28,
        p99_latency_ms=900.0,
        cpu_utilization=0.60,
    ),
    "auth": FakeScenario(
        name="auth",
        log_lines=[
            (1, "ERROR", "authentication rejected: certificate validation failed"),
            (2, "ERROR", "TLS handshake failure with identity provider"),
            (5, "WARN", "elevated login failure rate"),
            (10, "INFO", "session token validation degraded"),
        ],
        deployment=None,
        error_rate=0.15,
        p99_latency_ms=350.0,
        cpu_utilization=0.30,
    ),
    "latency": FakeScenario(
        name="latency",
        log_lines=[
            (1, "WARN", "p99 response latency exceeds 2000ms threshold"),
            (3, "WARN", "request queue depth elevated"),
            (6, "INFO", "elevated response time detected across endpoints"),
            (12, "INFO", "no error rate increase observed alongside latency rise"),
        ],
        deployment=None,
        error_rate=0.02,
        p99_latency_ms=6500.0,
        cpu_utilization=0.82,
    ),
    "generic": FakeScenario(
        name="generic",
        log_lines=[
            (3, "INFO", "no anomalies detected in the sampled window"),
            (8, "INFO", "request volume within normal range"),
        ],
        deployment=None,
        error_rate=0.01,
        p99_latency_ms=320.0,
        cpu_utilization=0.35,
    ),
}

# Checked in this fixed order; first keyword match wins. Overlaps are
# possible (this is a blunt keyword heuristic, not a classifier) and
# acceptable -- the goal is "varies sensibly by input", not "perfectly
# classifies every possible trigger".
_KEYWORD_ORDER: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("database", _DATABASE_KEYWORDS),
    ("deployment", _DEPLOYMENT_KEYWORDS),
    ("auth", _AUTH_KEYWORDS),
    ("latency", _LATENCY_KEYWORDS),
)

# Always present as the older deployment history entry, in addition to
# a scenario's own recent deploy (if it has one) -- keeps
# get_deployment_history's "usually 2 entries" shape.
OLD_DEPLOYMENT: tuple[int, str, str] = (2 * 24 * 60, "v1.41.3", "minor logging improvements")

# Phrases that negate whatever keyword immediately follows them (e.g. "No
# recent deployments" should NOT be read as a positive "deploy" signal).
# Checked within a small character window immediately before a keyword
# occurrence -- not a general negation parser, just enough to stop the
# most common "no X" false positive this stub actually hit.
_NEGATION_PHRASES = ("no recent", "not affected", "no known", "without any")
_NEGATION_WINDOW_CHARS = 20


def _is_negated(lowered_trigger: str, keyword_index: int) -> bool:
    window = lowered_trigger[max(0, keyword_index - _NEGATION_WINDOW_CHARS) : keyword_index]
    return any(phrase in window for phrase in _NEGATION_PHRASES)


def _keyword_matches(lowered_trigger: str, keyword: str) -> bool:
    """True if `keyword` appears in `lowered_trigger` at least once
    without being immediately preceded by a negation phrase. A keyword
    that only appears negated (e.g. "no recent deployments") does not
    count as a match; the same keyword appearing elsewhere, unnegated,
    still would."""
    start = 0
    while (index := lowered_trigger.find(keyword, start)) != -1:
        if not _is_negated(lowered_trigger, index):
            return True
        start = index + 1
    return False


def select_scenario(trigger: str) -> FakeScenario:
    lowered = trigger.lower()
    for name, keywords in _KEYWORD_ORDER:
        if any(_keyword_matches(lowered, keyword) for keyword in keywords):
            return _SCENARIOS[name]
    return _SCENARIOS["generic"]
