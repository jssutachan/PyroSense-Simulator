"""PyroSense simulation subsystem.

Two programs live here:

- ``planner``: site-planner — selects sensor placement over a DEM of the
  Cerros Orientales (Bogotá) and emits a deployment plan.
- ``fleet``: fleet-sim — simulates the deployed sensor fleet and publishes
  telemetry to AWS IoT Core over MQTT.

Shared building blocks:

- ``contracts``: message schemas and validation (the wire contract with the
  cloud backend).
- ``publishers``: transport adapters (MQTT/IoT Core, stdout, file).
"""

__version__ = "0.1.0"
