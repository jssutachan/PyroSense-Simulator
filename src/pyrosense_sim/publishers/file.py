"""NDJSON publisher to a file, with size-based rotation."""

from pathlib import Path
from typing import TextIO

from pyrosense_sim.contracts.telemetry import TelemetryPayload
from pyrosense_sim.publishers.ndjson import ndjson_line


class FilePublisher:
    """Appends one JSON line per payload; rotates when the file exceeds ``max_bytes``.

    Rotation renames the active file to ``<name>.<n>`` (``n`` increasing,
    resuming after any rotations left by a previous run) and reopens a
    fresh file at the original path. A payload is never split across
    files: the size check happens after each complete write.

    Not thread-safe: the simulator is single-threaded by design; revisit
    if the fleet engine ever publishes concurrently.
    """

    def __init__(self, path: Path | str, max_bytes: int = 1_000_000) -> None:
        """Open (or create) the target file in append mode.

        Args:
            path: Destination NDJSON file; parent directory must exist.
            max_bytes: Size threshold that triggers rotation after a write.

        Raises:
            ValueError: If ``max_bytes`` is not positive.
        """
        if max_bytes <= 0:
            msg = f"max_bytes must be positive, got {max_bytes}"
            raise ValueError(msg)
        self._path = Path(path)
        self._max_bytes = max_bytes
        self._rotations = self._last_rotation_index()
        self._file: TextIO = self._path.open("a", encoding="utf-8")

    def publish(self, payload: TelemetryPayload) -> None:
        """Append the payload as one NDJSON line, rotating afterwards if needed.

        Args:
            payload: Validated telemetry payload to persist.
        """
        self._file.write(ndjson_line(payload))
        self._file.flush()
        if self._file.tell() > self._max_bytes:
            self._rotate()

    def close(self) -> None:
        """Close the active file. Publishing after close is undefined behavior."""
        self._file.close()

    def _last_rotation_index(self) -> int:
        indexes = [
            int(suffix)
            for p in self._path.parent.glob(f"{self._path.name}.*")
            if (suffix := p.name.removeprefix(f"{self._path.name}.")).isdigit()
        ]
        return max(indexes, default=0)

    def _rotate(self) -> None:
        self._file.close()
        self._rotations += 1
        self._path.rename(self._path.with_name(f"{self._path.name}.{self._rotations}"))
        self._file = self._path.open("a", encoding="utf-8")
