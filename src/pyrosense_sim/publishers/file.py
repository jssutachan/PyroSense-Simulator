"""NDJSON publisher to a file, with size-based rotation."""

from pathlib import Path
from typing import TextIO

from pyrosense_sim.contracts.telemetry import TelemetryPayload


class FilePublisher:
    """Appends one JSON line per payload; rotates when the file exceeds ``max_bytes``.

    Rotation renames the active file to ``<name>.<n>`` (``n`` increasing,
    resuming after any rotations left by a previous run) and reopens a
    fresh file at the original path. A payload is never split across
    files: the size check happens after each complete write.
    """

    def __init__(self, path: Path | str, max_bytes: int = 1_000_000) -> None:
        if max_bytes <= 0:
            msg = f"max_bytes must be positive, got {max_bytes}"
            raise ValueError(msg)
        self._path = Path(path)
        self._max_bytes = max_bytes
        self._rotations = self._last_rotation_index()
        self._file: TextIO = self._path.open("a", encoding="utf-8")

    def publish(self, payload: TelemetryPayload) -> None:
        self._file.write(payload.model_dump_json() + "\n")
        self._file.flush()
        if self._file.tell() > self._max_bytes:
            self._rotate()

    def close(self) -> None:
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
