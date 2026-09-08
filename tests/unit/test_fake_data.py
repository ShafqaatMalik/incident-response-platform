from app.tools.fake_data import select_scenario


def test_database_keyword_selects_database_scenario() -> None:
    assert select_scenario("The primary database is unreachable").name == "database"


def test_deploy_keyword_selects_deployment_scenario() -> None:
    assert select_scenario("New deploy v3.0.0 rolled out").name == "deployment"


def test_certificate_keyword_selects_auth_scenario() -> None:
    assert select_scenario("TLS certificate for the identity provider expired").name == "auth"


def test_latency_keyword_selects_latency_scenario() -> None:
    assert select_scenario("p99 latency has climbed sharply").name == "latency"


def test_unmatched_trigger_falls_back_to_generic() -> None:
    assert select_scenario("A flock of geese landed on the runway").name == "generic"


def test_empty_trigger_falls_back_to_generic() -> None:
    assert select_scenario("").name == "generic"


def test_matching_is_case_insensitive() -> None:
    assert select_scenario("DATABASE connection issues").name == "database"


def test_fixed_precedence_order_wins_on_overlap() -> None:
    # Contains both a database keyword ("database") and a deployment keyword
    # ("deploy") -- database is checked first in fake_data.py's
    # _KEYWORD_ORDER, so it should win deterministically.
    trigger = "The database deploy is failing"
    assert select_scenario(trigger).name == "database"


# --- negation handling ---


def test_auth_001_style_trigger_is_not_misread_as_a_deployment() -> None:
    # Real evaluation scenario auth_001's trigger -- "No recent deployments"
    # previously matched the "deploy" keyword despite explicitly ruling a
    # deployment out, stealing this into the deployment bucket instead of auth.
    trigger = (
        "Login success rate dropped from 99% to 40% starting 09:12 UTC. "
        "No recent deployments. Certificate for the identity provider "
        "integration expired at 09:10 UTC."
    )
    assert select_scenario(trigger).name == "auth"


def test_api_002_style_trigger_falls_back_to_generic_not_deployment() -> None:
    # Real evaluation scenario api_002's trigger -- same "No recent
    # deployments" false positive, previously fabricating a deploy story for
    # a scenario whose whole point is testing the agent doesn't invent one.
    trigger = (
        "The /v1/search endpoint has started returning malformed JSON "
        "(missing closing braces) for approximately 8% of requests since "
        "10:15 UTC. No recent deployments. CPU and memory on all instances "
        "are normal."
    )
    assert select_scenario(trigger).name == "generic"


def test_negated_keyword_does_not_match_but_unnegated_occurrence_elsewhere_still_does() -> None:
    # "deploy" appears twice: once negated ("no recent deploy"), once not
    # ("deploy pipeline is stuck") -- the unnegated occurrence should still
    # win the match.
    trigger = "No recent deploy here, but the deploy pipeline is stuck"
    assert select_scenario(trigger).name == "deployment"


def test_negation_only_suppresses_the_keyword_it_precedes() -> None:
    # "No known" negates "database" here, but "certificate" (unrelated,
    # un-negated) should still make this match auth.
    trigger = "No known database issues; certificate validation is failing"
    assert select_scenario(trigger).name == "auth"
