#!/usr/bin/env python3
"""Sends one realistic POST /documents request to the live incident-
response-platform API, then exits. Run periodically as a Cloud Run Job
via Cloud Scheduler -- see scripts/synthetic_traffic/Dockerfile.
"""

import json
import logging
import os
import random
import sys
import urllib.error
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("synthetic_traffic")

SAMPLE_TEXTS: list[tuple[str, str]] = [
    (
        "Kubernetes Cluster Autoscaling",
        "Horizontal pod autoscaling adjusts the number of running replicas "
        "based on observed CPU utilization or custom metrics. Cluster "
        "autoscaling goes a step further, adding or removing nodes "
        "entirely as workload demand shifts. Together they let a team "
        "run lean during quiet periods without manually intervening "
        "during traffic spikes.",
    ),
    (
        "Sourdough Starter Maintenance",
        "A sourdough starter is a living culture of wild yeast and "
        "lactic acid bacteria, fed regularly with flour and water. "
        "Daily feedings at room temperature keep it active, while "
        "refrigeration slows fermentation for less frequent maintenance. "
        "A starter that smells sharply of vinegar rather than yeast has "
        "usually gone too long between feedings.",
    ),
    (
        "Urban Cycling Infrastructure",
        "Protected bike lanes, separated from car traffic by a physical "
        "barrier, consistently show lower injury rates than painted "
        "lanes alone. Cities that build connected networks rather than "
        "isolated segments see the largest increases in ridership. "
        "Intersection design matters as much as the lanes themselves, "
        "since most cyclist injuries happen at crossings.",
    ),
    (
        "Migratory Bird Navigation",
        "Many migratory birds rely on a combination of the sun's "
        "position, star patterns, and the Earth's magnetic field to "
        "navigate thousands of kilometers each season. Some species can "
        "recalibrate their internal compass using the sunset horizon "
        "even after being displaced far off course. Researchers still "
        "don't fully understand how these cues are integrated in the "
        "avian brain.",
    ),
    (
        "Personal Emergency Fund Sizing",
        "Financial advisors commonly suggest three to six months of "
        "essential expenses as a starting point for an emergency fund. "
        "Households with a single income earner or irregular income "
        "often benefit from sizing closer to the higher end of that "
        "range. Keeping the fund in a high-yield savings account rather "
        "than investments preserves quick access without market risk.",
    ),
    (
        "Deep Sea Hydrothermal Vents",
        "Hydrothermal vents on the ocean floor support ecosystems that "
        "rely on chemosynthesis rather than sunlight, with bacteria "
        "converting hydrogen sulfide into energy. Tube worms, vent "
        "crabs, and other species form dense communities around these "
        "vents despite crushing pressure and near-freezing surrounding "
        "water. Some of these ecosystems were only discovered in the "
        "late 1970s, reshaping assumptions about where life can exist.",
    ),
    (
        "Remote Team Onboarding",
        "New hires on distributed teams often lose the informal context "
        "that in-office colleagues absorb by osmosis, like how decisions "
        "actually get made or who to ask about a specific system. "
        "Structured onboarding docs help, but pairing a new hire with a "
        "dedicated buddy for the first few weeks tends to close that gap "
        "faster than documentation alone.",
    ),
    (
        "Public Library Digital Lending",
        "Digital lending platforms let public libraries offer e-books "
        "and audiobooks under licensing terms that are often more "
        "restrictive and expensive than print. Some publishers cap the "
        "number of loans a single digital copy can fulfill before the "
        "library must repurchase it. This has pushed some library "
        "systems to negotiate collectively for better terms.",
    ),
]


def pick_sample(rng: random.Random | None = None) -> tuple[str, str]:
    return (rng or random).choice(SAMPLE_TEXTS)


def build_request(base_url: str, api_key: str, title: str, text: str) -> urllib.request.Request:
    url = base_url.rstrip("/") + "/documents"
    body = json.dumps({"title": title, "text": text}).encode("utf-8")
    return urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
        method="POST",
    )


def send_once(base_url: str, api_key: str, *, timeout: float = 10.0) -> bool:
    title, text = pick_sample()
    request = build_request(base_url, api_key, title, text)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            logger.info("sent synthetic document %r -> HTTP %s", title, response.status)
            return True
    except (urllib.error.URLError, TimeoutError) as exc:
        # A single failed ping is low-stakes and expected occasionally
        # (cold start, transient network blip) -- log and exit cleanly
        # rather than raising, so Cloud Scheduler doesn't see a crash for
        # something this unimportant.
        logger.warning("synthetic traffic request failed (continuing): %s", exc)
        return False


def main() -> int:
    try:
        base_url = os.environ["TARGET_BASE_URL"]
        api_key = os.environ["API_KEY"]
    except KeyError as exc:
        # Missing config is a real deployment bug, not a transient blip --
        # this should fail loudly and visibly in the Job's execution status.
        logger.error("missing required environment variable: %s", exc)
        return 1

    send_once(base_url, api_key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
