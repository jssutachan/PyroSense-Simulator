"""Drift guard: the committed JSON Schema must match the live model."""

import json
from pathlib import Path

import pytest

from pyrosense_sim.contracts.export_schema import main, render_schema

SCHEMA_FILE = Path(__file__).parents[2] / "docs" / "payload-schema-v1.json"


def test_committed_schema_matches_model() -> None:
    assert SCHEMA_FILE.read_text(encoding="utf-8") == render_schema(), (
        "docs/payload-schema-v1.json is stale; regenerate it with "
        "'python -m pyrosense_sim.contracts.export_schema > docs/payload-schema-v1.json'"
    )


def test_schema_forbids_extra_properties() -> None:
    schema = json.loads(render_schema())
    assert schema["additionalProperties"] is False


def test_main_prints_schema_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    assert capsys.readouterr().out == render_schema()
