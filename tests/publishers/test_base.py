"""Interface conformance: every concrete publisher must satisfy the Publisher protocol."""

import io
from pathlib import Path

from pyrosense_sim.publishers.base import Publisher
from pyrosense_sim.publishers.file import FilePublisher
from pyrosense_sim.publishers.stdout import StdoutPublisher


def test_stdout_publisher_satisfies_protocol() -> None:
    publisher = StdoutPublisher(stream=io.StringIO())
    assert isinstance(publisher, Publisher)


def test_file_publisher_satisfies_protocol(tmp_path: Path) -> None:
    publisher = FilePublisher(tmp_path / "t.ndjson")
    try:
        assert isinstance(publisher, Publisher)
    finally:
        publisher.close()
