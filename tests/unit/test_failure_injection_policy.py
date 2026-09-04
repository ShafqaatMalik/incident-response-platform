from app.policies.failure_injection_policy import (
    FailureCategory,
    build_injection_trigger,
    is_over_cap,
)


def test_under_limit_is_not_exceeded() -> None:
    assert is_over_cap(4, 5) is False


def test_at_limit_is_exceeded() -> None:
    assert is_over_cap(5, 5) is True


def test_over_limit_is_exceeded() -> None:
    assert is_over_cap(6, 5) is True


def test_zero_count_against_positive_limit_is_not_exceeded() -> None:
    assert is_over_cap(0, 5) is False


def test_dependency_timeout_trigger_is_specific() -> None:
    trigger, evidence = build_injection_trigger(FailureCategory.DEPENDENCY_TIMEOUT)
    assert "timeout" in trigger.lower()
    assert "database" in trigger.lower() or "postgres" in trigger.lower()
    assert evidence


def test_elevated_error_rate_trigger_is_specific() -> None:
    trigger, evidence = build_injection_trigger(FailureCategory.ELEVATED_ERROR_RATE)
    assert "500" in trigger
    assert "requests" in trigger.lower()
    assert evidence


def test_latency_spike_trigger_is_specific() -> None:
    trigger, evidence = build_injection_trigger(FailureCategory.LATENCY_SPIKE)
    assert "latency" in trigger.lower()
    assert "p99" in trigger.lower()
    assert evidence


def test_all_categories_produce_distinct_triggers() -> None:
    triggers = {build_injection_trigger(category)[0] for category in FailureCategory}
    assert len(triggers) == len(FailureCategory)
