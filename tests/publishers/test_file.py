"""Tests for FilePublisher: NDJSON to file with size-based rotation."""

import json
from pathlib import Path

import pytest

from pyrosense_sim.contracts.telemetry import TelemetryPayload
from pyrosense_sim.publishers.file import FilePublisher
from tests.contracts.test_telemetry import valid_kwargs


def make_payload(seq: int = 0) -> TelemetryPayload:
    return TelemetryPayload(**valid_kwargs(seq=seq))


def test_writes_parseable_ndjson(tmp_path: Path) -> None:
    target = tmp_path / "telemetry.ndjson"
    publisher = FilePublisher(target, max_bytes=1_000_000)

    for seq in range(3):
        publisher.publish(make_payload(seq))
    publisher.close()

    lines = target.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["seq"] for line in lines] == [0, 1, 2]


def test_rotates_when_size_exceeded(tmp_path: Path) -> None:
    target = tmp_path / "telemetry.ndjson"
    # Any payload line is > 100 bytes, so every publish triggers a rotation.
    publisher = FilePublisher(target, max_bytes=100)

    for seq in range(3):
        publisher.publish(make_payload(seq))
    publisher.close()

    rotated = sorted(tmp_path.glob("telemetry.ndjson.*"))
    expected_names = ["telemetry.ndjson.1", "telemetry.ndjson.2", "telemetry.ndjson.3"]
    assert [p.name for p in rotated] == expected_names
    # Each rotated file holds exactly one intact payload.
    for expected_seq, rotated_file in enumerate(rotated):
        lines = rotated_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["seq"] == expected_seq


def test_no_rotation_below_threshold(tmp_path: Path) -> None:
    target = tmp_path / "telemetry.ndjson"
    publisher = FilePublisher(target, max_bytes=1_000_000)
    publisher.publish(make_payload())
    publisher.close()

    assert list(tmp_path.glob("telemetry.ndjson.*")) == []


def test_rotation_resumes_after_previous_runs(tmp_path: Path) -> None:
    target = tmp_path / "telemetry.ndjson"
    leftover = tmp_path / "telemetry.ndjson.4"
    leftover.write_text("previous run\n", encoding="utf-8")

    publisher = FilePublisher(target, max_bytes=100)
    publisher.publish(make_payload())
    publisher.close()

    # History from the previous run is preserved, new rotation continues at .5
    assert leftover.read_text(encoding="utf-8") == "previous run\n"
    assert (tmp_path / "telemetry.ndjson.5").exists()


def test_rejects_non_positive_max_bytes(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="max_bytes must be positive"):
        FilePublisher(tmp_path / "t.ndjson", max_bytes=0)
