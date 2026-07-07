"""End-to-end tests for FleetOrchestrator: contract validity, determinism, SIGINT."""

import io
import json
from collections import defaultdict
from pathlib import Path

import pytest

from pyrosense_sim.contracts.telemetry import TelemetryPayload
from pyrosense_sim.fleet.config import ScenarioConfig, load_scenario
from pyrosense_sim.fleet.orchestrator import FleetOrchestrator
from pyrosense_sim.publishers.stdout import StdoutPublisher
from tests.fleet.site_fixture import write_site

REPO_ROOT = Path(__file__).parents[2]


def no_sleep(_: float) -> None:
    return None


def short_scenario(seed: int = 5) -> ScenarioConfig:
    return ScenarioConfig(name="test", duration_hours=0.5, seed=seed)


def run_to_string(tmp_path: Path, scenario: ScenarioConfig, node_count: int = 3) -> str:
    site = write_site(tmp_path / "sensores.geojson", node_count)
    stream = io.StringIO()
    orchestrator = FleetOrchestrator.from_files(
        site, scenario, StdoutPublisher(stream=stream), sleep_fn=no_sleep
    )
    summary = orchestrator.run()
    assert not summary.interrupted
    return stream.getvalue()


class TestEndToEnd:
    def test_every_line_is_a_valid_v1_payload(self, tmp_path: Path) -> None:
        lines = run_to_string(tmp_path, short_scenario()).splitlines()
        assert lines
        for line in lines:
            TelemetryPayload.model_validate(json.loads(line))  # raises if invalid

    def test_seq_is_strictly_monotonic_per_device(self, tmp_path: Path) -> None:
        lines = run_to_string(tmp_path, short_scenario()).splitlines()
        seqs: dict[str, list[int]] = defaultdict(list)
        for line in lines:
            record = json.loads(line)
            seqs[record["device_id"]].append(record["seq"])
        assert len(seqs) == 3
        for device_id, values in seqs.items():
            assert values == list(range(len(values))), device_id

    def test_sample_count_matches_cadence(self, tmp_path: Path) -> None:
        # 0.5 h horizon, t_normal 300 s -> 6 samples per node, 3 nodes.
        lines = run_to_string(tmp_path, short_scenario()).splitlines()
        assert len(lines) == 18

    def test_baseline_scenario_runs_without_aws(self, tmp_path: Path) -> None:
        scenario = load_scenario(REPO_ROOT / "scenarios" / "baseline.yaml")
        fast = scenario.model_copy(update={"duration_hours": 0.25})
        output = run_to_string(tmp_path, fast)
        statuses = {json.loads(line)["status"] for line in output.splitlines()}
        assert statuses == {"OK"}  # healthy operation, no alerts, no AWS anywhere


class TestDeterminism:
    def test_same_seed_produces_identical_stream(self, tmp_path: Path) -> None:
        first = run_to_string(tmp_path, short_scenario(seed=7))
        second = run_to_string(tmp_path, short_scenario(seed=7))
        assert first == second

    def test_different_seed_differs(self, tmp_path: Path) -> None:
        first = run_to_string(tmp_path, short_scenario(seed=1))
        second = run_to_string(tmp_path, short_scenario(seed=2))
        assert first != second


class TestInterruption:
    def test_sigint_closes_cleanly_with_summary(self, tmp_path: Path) -> None:
        site = write_site(tmp_path / "sensores.geojson")

        class InterruptingPublisher:
            def __init__(self) -> None:
                self.published = 0
                self.closed = False

            def publish(self, payload: TelemetryPayload) -> None:
                self.published += 1
                if self.published == 5:
                    raise KeyboardInterrupt

            def close(self) -> None:
                self.closed = True

        publisher = InterruptingPublisher()
        orchestrator = FleetOrchestrator.from_files(
            site, short_scenario(), publisher, sleep_fn=no_sleep
        )
        summary = orchestrator.run()

        assert summary.interrupted
        assert publisher.closed  # flush/close happened despite the interrupt
        assert summary.emitted == 4  # the fifth publish never completed
        assert sum(summary.by_status.values()) == 4


class TestSitePlanValidation:
    def test_empty_plan_is_rejected(self, tmp_path: Path) -> None:
        site = tmp_path / "empty.geojson"
        site.write_text('{"type": "FeatureCollection", "features": []}', encoding="utf-8")
        with pytest.raises(ValueError, match="no features"):
            FleetOrchestrator.from_files(
                site, short_scenario(), StdoutPublisher(stream=io.StringIO())
            )

    def test_missing_properties_are_rejected(self, tmp_path: Path) -> None:
        site = tmp_path / "bad.geojson"
        site.write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {"type": "Point", "coordinates": [-74.05, 4.55]},
                            "properties": {"device_id": "PYRO-T1-0001"},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="misses properties"):
            FleetOrchestrator.from_files(
                site, short_scenario(), StdoutPublisher(stream=io.StringIO())
            )
