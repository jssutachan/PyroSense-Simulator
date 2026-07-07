"""Simulation scheduler: orders node emissions on a simulated clock.

A min-heap keyed by (next sample time, device_id) yields nodes in
deterministic order — the device_id tiebreak matters: without it, two
nodes due at the same instant would compare by object identity and the
run would stop being reproducible.

Real-time pacing is ``simulated_dt / speed`` via an injectable sleep
function: ``speed=60`` plays an hour per real minute, large speeds run
effectively as fast as possible, and tests inject a no-op sleep.
"""

import time
from collections.abc import Callable, Iterator, Sequence
from heapq import heapify, heappop, heappush

from pyrosense_sim.fleet.node import SensorNode


class Scheduler:
    """Yields ``(sim_time, node)`` pairs in emission order until the horizon."""

    def __init__(
        self,
        nodes: Sequence[SensorNode],
        *,
        duration_s: float,
        speed: float = 60.0,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        """Configure the run.

        Args:
            nodes: The fleet (at least one node).
            duration_s: Simulated horizon in seconds; emissions happen at
                times ``t < duration_s``.
            speed: Simulated-to-real time factor (60 = one simulated hour
                per real minute). Must be positive.
            sleep_fn: Injected pacing function; defaults to
                ``time.sleep``. Tests pass a no-op.

        Raises:
            ValueError: If ``nodes`` is empty, or ``duration_s``/``speed``
                are not positive.
        """
        if not nodes:
            msg = "scheduler needs at least one node"
            raise ValueError(msg)
        if duration_s <= 0 or speed <= 0:
            msg = f"duration_s and speed must be positive, got {duration_s}, {speed}"
            raise ValueError(msg)
        self._nodes = tuple(nodes)
        self._duration_s = duration_s
        self._speed = speed
        self._sleep = sleep_fn

    def run(self) -> Iterator[tuple[float, SensorNode]]:
        """Iterate emissions in simulated-time order, pacing real time.

        Yields:
            ``(sim_time_s, node)`` for every due sample. After the caller
            consumes a pair, the node is re-scheduled at
            ``sim_time_s + node.interval_s`` — so a node that switched to
            its alert cadence is re-heaped accordingly.
        """
        heap: list[tuple[float, str, SensorNode]] = [
            (0.0, node.device_id, node) for node in self._nodes
        ]
        heapify(heap)
        now_s = 0.0
        while heap:
            t_s, device_id, node = heappop(heap)
            if t_s >= self._duration_s:
                continue  # this node is past the horizon; let the heap drain
            self._sleep((t_s - now_s) / self._speed)
            now_s = t_s
            yield t_s, node
            heappush(heap, (t_s + node.interval_s, device_id, node))
