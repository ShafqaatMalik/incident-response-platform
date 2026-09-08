#!/usr/bin/env python3
"""Runs the full 18-scenario evaluation harness against the full agent
pipeline, using live models -- costs real money. See
ARCHITECTURE.md §11 and STATUS.md for design/rationale.

Run explicitly: `uv run python evaluation/run.py`
"""

import asyncio
import logging
import sys
from pathlib import Path

from harness import run_scenario
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from report import write_report
from scenarios import ScenarioSetValidationError, load_scenarios, validate_scenario_set

from app.core.config import get_settings
from app.db.session import get_sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("evaluation")

SCENARIOS_PATH = Path(__file__).parent / "scenarios.yaml"


def _configure_in_memory_tracing() -> InMemorySpanExporter:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return exporter


async def main() -> int:
    try:
        scenarios = load_scenarios(SCENARIOS_PATH)
        validate_scenario_set(scenarios)
    except ScenarioSetValidationError as exc:
        logger.error("scenario set failed validation: %s", exc)
        return 1

    settings = get_settings()
    exporter = _configure_in_memory_tracing()
    sessionmaker = get_sessionmaker()

    results = []
    async with sessionmaker() as session:
        for i, scenario in enumerate(scenarios, start=1):
            logger.info(
                "[%d/%d] running %s (%s)", i, len(scenarios), scenario.id, scenario.category
            )
            result = await run_scenario(scenario, session, settings, exporter)
            if result.harness_error:
                logger.warning("  aborted: %s", result.harness_error)
            else:
                logger.info(
                    "  final status: %s, cost: $%.4f",
                    result.rule_based.final_status if result.rule_based else "unknown",
                    float(result.rule_based.cost_usd) if result.rule_based else 0.0,
                )
            results.append(result)

    json_path, md_path = write_report(results)
    logger.info("report written: %s / %s", json_path, md_path)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
