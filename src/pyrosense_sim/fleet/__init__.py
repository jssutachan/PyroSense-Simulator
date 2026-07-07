"""Fleet-sim: the simulated sensor fleet.

Consumes the ``sensores.geojson`` plan from the site-planner and emits
contract-valid telemetry through an injected publisher. Composition:
``config`` (scenario YAML boundary) -> ``environment`` (ground truth)
-> ``node`` (noisy instrument) -> ``scheduler`` (simulated clock) ->
``orchestrator`` (wiring + clean shutdown) -> ``cli`` (fleet-sim).
"""
