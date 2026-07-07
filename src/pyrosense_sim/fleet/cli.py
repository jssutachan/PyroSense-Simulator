"""Command-line interface of the fleet simulator.

Runs entirely without AWS credentials: the default publisher writes
NDJSON to **stdout** (the data channel) while logs go to **stderr**, so
``fleet-sim run ... | head`` and pipes into other tools stay clean
(ADR-0010).

Example:
    fleet-sim run --site out/sensores.geojson \\
        --scenario scenarios/baseline.yaml --publisher stdout --speed 60
"""

import logging
import sys
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from pyrosense_sim.fleet.config import load_scenario
from pyrosense_sim.fleet.orchestrator import FleetOrchestrator
from pyrosense_sim.publishers.base import Publisher
from pyrosense_sim.publishers.file import FilePublisher
from pyrosense_sim.publishers.stdout import StdoutPublisher

app = typer.Typer(
    name="fleet-sim",
    help="Simula la flota de sensores PyroSense y publica su telemetría.",
    no_args_is_help=True,
)


class PublisherKind(StrEnum):
    """Available transports."""

    STDOUT = "stdout"
    FILE = "file"
    MQTT = "mqtt"


@app.callback()
def _root() -> None:
    """Fleet-sim de PyroSense: del plan de despliegue a la telemetría."""


@app.command()
def run(
    site: Annotated[
        Path,
        typer.Option(exists=True, dir_okay=False, help="sensores.geojson del site-planner."),
    ],
    scenario: Annotated[Path, typer.Option(exists=True, dir_okay=False, help="Escenario YAML.")],
    publisher: Annotated[
        PublisherKind, typer.Option(help="Transporte de salida.")
    ] = PublisherKind.STDOUT,
    out: Annotated[
        Path, typer.Option(help="Archivo NDJSON destino (solo --publisher file).")
    ] = Path("out/telemetry.ndjson"),
    speed: Annotated[
        float, typer.Option(min=0.000001, help="Factor de aceleración (60 = 1 h sim/min real).")
    ] = 60.0,
) -> None:
    """Run a scenario against the planned fleet until its horizon (or Ctrl-C)."""
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,  # stdout is the data channel (NDJSON)
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = load_scenario(scenario)
    sink = _build_publisher(publisher, out)
    orchestrator = FleetOrchestrator.from_files(site, config, sink, speed=speed)
    summary = orchestrator.run()
    raise typer.Exit(code=130 if summary.interrupted else 0)


def _build_publisher(kind: PublisherKind, out: Path) -> Publisher:
    if kind is PublisherKind.FILE:
        out.parent.mkdir(parents=True, exist_ok=True)
        return FilePublisher(out)
    if kind is PublisherKind.MQTT:
        # Lazy import: the offline transports never touch AWS code paths.
        from pyrosense_sim.publishers.mqtt import MqttPublisher

        return MqttPublisher()  # settings from env/.env; fails early if missing
    return StdoutPublisher()


def main() -> None:
    """Console-script entry point."""
    app()
