"""Tests for the load scenario: fleet replication with derived device ids."""

import io
import re
from pathlib import Path

import pytest

from pyrosense_sim.fleet.config import LoadConfig, ScenarioConfig, load_scenario
from pyrosense_sim.fleet.orchestrator import FleetOrchestrator
from pyrosense_sim.publishers.stdout import StdoutPublisher
from tests.fleet.site_fixture import write_site

REPO_ROOT = Path(__file__).parents[2]


def no_sleep(_: float) -> None:
    return None


def multiplied_scenario(multiplier: int) -> ScenarioConfig:
    return ScenarioConfig(
        name="load-test",
        duration_hours=0.25,
        seed=9,
        load=LoadConfig(fleet_multiplier=multiplier),
    )


def build_orchestrator(tmp_path: Path, multiplier: int) -> FleetOrchestrator:
    site = write_site(tmp_path / "sensores.geojson", node_count=3)
    return FleetOrchestrator.from_files(
        site,
        multiplied_scenario(multiplier),
        StdoutPublisher(stream=io.StringIO()),
        sleep_fn=no_sleep,
    )


def test_multiplier_replicates_the_fleet_with_unique_valid_ids(tmp_path: Path) -> None:
    orchestrator = build_orchestrator(tmp_path, multiplier=3)
    nodes = orchestrator._nodes

    assert len(nodes) == 9  # 3 originals x 3
    device_ids = [node.device_id for node in nodes]
    assert len(set(device_ids)) == 9  # no collisions
    pattern = re.compile(r"^PYRO-T1-\d{4}$")
    assert all(pattern.match(device_id) for device_id in device_ids)
    # Originals preserved; replicas derived past the original max serial.
    assert "PYRO-T1-0001" in device_ids
    assert "PYRO-T1-0004" in device_ids  # first replica of position 1
    assert "PYRO-T1-0009" in device_ids  # last replica


def test_multiplied_fleet_multiplies_the_emissions(tmp_path: Path) -> None:
    site = write_site(tmp_path / "sensores.geojson", node_count=3)
    outputs: list[int] = []
    for multiplier in (1, 3):
        stream = io.StringIO()
        FleetOrchestrator.from_files(
            site,
            multiplied_scenario(multiplier),
            StdoutPublisher(stream=stream),
            sleep_fn=no_sleep,
        ).run()
        outputs.append(len(stream.getvalue().splitlines()))
    assert outputs[1] == outputs[0] * 3


def test_multiplier_one_is_a_no_op(tmp_path: Path) -> None:
    orchestrator = build_orchestrator(tmp_path, multiplier=1)
    assert len(orchestrator._nodes) == 3


def test_serial_overflow_is_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="overflows the 4-digit device_id"):
        build_orchestrator(tmp_path, multiplier=4000)


def test_shipped_carga_scenario_multiplies_and_accelerates() -> None:
    config = load_scenario(REPO_ROOT / "scenarios" / "carga.yaml")
    assert config.load.fleet_multiplier == 5
    assert config.node.t_normal_s == 60.0
    assert not config.fires  # clean signal, pure volume
    assert config.faults is None
