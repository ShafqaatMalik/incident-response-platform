import os
from functools import lru_cache

import anthropic


@lru_cache
def get_anthropic_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic()


def has_anthropic_credentials() -> bool:
    """Best-effort check for startup warnings only.

    Checks the two env-var credential sources directly rather than
    constructing a client — anthropic.AsyncAnthropic() does not validate
    credentials at construction time (confirmed empirically: it succeeds
    even with zero credential sources configured; the SDK only raises,
    lazily, on the first actual request). This heuristic does not detect
    an active `ant auth login` profile — not a concern for this project's
    deployment model (Cloud Run env vars), but worth knowing if run
    locally under a profile-based login with no env var set.
    """
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
