"""Tests for StdoutPublisher: one parseable NDJSON line per payload, no AWS."""

import io
import json

import pytest

from pyrosense_sim.contracts.telemetry import TelemetryPayload
from pyrosense_sim.publishers.stdout import StdoutPublisher
from tests.contracts.test_telemetry import valid_kwargs


def test_emits_exactly_one_json_line_per_payload() -> None:
    stream = io.StringIO()
    publisher = StdoutPublisher(stream=stream)

    payloads = [TelemetryPayload(**valid_kwargs(seq=i)) for i in range(3)]
    for payload in payloads:
        publisher.publish(payload)
    publisher.close()

    lines = stream.getvalue().splitlines()
    assert len(lines) == 3
    for line, original in zip(lines, payloads, strict=True):
        assert TelemetryPayload.model_validate(json.loads(line)) == original


def test_defaults_to_sys_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    publisher = StdoutPublisher()
    publisher.publish(TelemetryPayload(**valid_kwargs()))
    publisher.close()

    out = capsys.readouterr().out
    assert out.endswith("\n")
    assert json.loads(out)["device_id"] == "PYRO-T1-0042"


def test_close_does_not_close_the_stream() -> None:
    stream = io.StringIO()
    publisher = StdoutPublisher(stream=stream)
    publisher.close()
    assert not stream.closed
