"""Export the telemetry payload v1 contract as JSON Schema.

Regenerate the committed schema after any (versioned!) contract change:

    python -m pyrosense_sim.contracts.export_schema > docs/payload-schema-v1.json

A test guards against drift between the model and the committed file.
"""

import json

from pyrosense_sim.contracts.telemetry import TelemetryPayload


def render_schema() -> str:
    """Return the v1 payload JSON Schema, pretty-printed with stable key order."""
    return json.dumps(TelemetryPayload.model_json_schema(), indent=2, sort_keys=True) + "\n"


def main() -> None:
    print(render_schema(), end="")


if __name__ == "__main__":
    main()
