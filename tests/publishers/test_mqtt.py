"""Tests for MqttPublisher against a mocked broker (no AWS anywhere)."""

import logging
import random
from pathlib import Path

import pytest

from pyrosense_sim.publishers.base import Publisher
from pyrosense_sim.publishers.mqtt import QOS_AT_LEAST_ONCE, MqttPublisher, MqttSettings
from tests.fleet.test_faults import make_payload

SECRET_ENDPOINT = "zzz-secret-endpoint-ats.iot.us-east-1.amazonaws.com"
SECRET_KEY_PATH = "certs/super-secret-private.pem.key"


class FakeBroker:
    """Mock broker: programmable failures, records everything."""

    def __init__(self, fail_first_publishes: int = 0, fail_connects: int = 0) -> None:
        self.fail_first_publishes = fail_first_publishes
        self.fail_connects = fail_connects
        self.connect_calls = 0
        self.published: list[tuple[str, bytes, int]] = []
        self.disconnected = False

    def connect(self) -> None:
        self.connect_calls += 1
        if self.connect_calls <= self.fail_connects:
            msg = "connection refused"
            raise ConnectionError(msg)

    def publish(self, topic: str, payload: bytes, qos: int) -> None:
        if self.fail_first_publishes > 0:
            self.fail_first_publishes -= 1
            msg = "puback timeout"
            raise TimeoutError(msg)
        self.published.append((topic, payload, qos))

    def disconnect(self) -> None:
        self.disconnected = True


def make_settings() -> MqttSettings:
    return MqttSettings(
        _env_file=None,
        iot_endpoint=SECRET_ENDPOINT,
        cert_path=Path("certs/device.pem.crt"),
        private_key_path=Path(SECRET_KEY_PATH),
        root_ca_path=Path("certs/AmazonRootCA1.pem"),
    )


def make_publisher(broker: FakeBroker, **overrides: object) -> MqttPublisher:
    kwargs: dict[str, object] = {
        "connection": broker,
        "max_retries": 3,
        "base_backoff_s": 0.5,
        "rng": random.Random(1),
        "sleep_fn": lambda _: None,
    }
    kwargs.update(overrides)
    return MqttPublisher(make_settings(), **kwargs)  # type: ignore[arg-type]


def test_satisfies_publisher_protocol() -> None:
    assert isinstance(make_publisher(FakeBroker()), Publisher)


class TestHappyPath:
    def test_publishes_on_the_device_topic_at_qos1(self) -> None:
        broker = FakeBroker()
        publisher = make_publisher(broker)
        publisher.publish(make_payload(device_id="PYRO-T2-0007"))
        publisher.close()

        (topic, body, qos), *_ = broker.published
        assert topic == "pyrosense/dev/telemetry/PYRO-T2-0007"
        assert qos == QOS_AT_LEAST_ONCE
        assert b'"device_id":"PYRO-T2-0007"' in body
        assert broker.disconnected

    def test_connects_lazily_once(self) -> None:
        broker = FakeBroker()
        publisher = make_publisher(broker)
        assert broker.connect_calls == 0
        publisher.publish(make_payload(seq=0))
        publisher.publish(make_payload(seq=1))
        assert broker.connect_calls == 1


class TestBackoffAndRecovery:
    def test_exponential_backoff_with_bounded_jitter(self) -> None:
        sleeps: list[float] = []
        broker = FakeBroker(fail_first_publishes=3)
        publisher = make_publisher(broker, sleep_fn=sleeps.append)
        publisher.publish(make_payload())

        assert len(broker.published) == 1  # eventually delivered
        assert len(sleeps) == 3
        for attempt, delay in enumerate(sleeps):
            base = 0.5 * (2.0**attempt)
            assert base <= delay <= base + 0.5  # exponential + jitter in [0, base_backoff)
        assert sleeps[0] < sleeps[1] < sleeps[2]

    def test_reconnects_after_a_failure(self) -> None:
        broker = FakeBroker(fail_first_publishes=1)
        publisher = make_publisher(broker)
        publisher.publish(make_payload())
        # First attempt failed -> connection flagged dead -> reconnected.
        assert broker.connect_calls == 2
        assert len(broker.published) == 1

    def test_exhausted_retries_drop_and_count_without_raising(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        broker = FakeBroker(fail_first_publishes=99)
        publisher = make_publisher(broker)
        with caplog.at_level(logging.DEBUG):
            publisher.publish(make_payload())  # must not raise
            publisher.close()
        assert broker.published == []
        assert "failed after 3 retries" in caplog.text
        assert "failed=1" in caplog.text  # final metrics


class TestSecretsNeverLogged:
    def test_no_secret_appears_in_any_log_record(self, caplog: pytest.LogCaptureFixture) -> None:
        broker = FakeBroker(fail_first_publishes=2)
        publisher = make_publisher(broker, metrics_interval_s=0.0)
        with caplog.at_level(logging.DEBUG):
            publisher.publish(make_payload())
            publisher.close()

        assert caplog.text  # we did log things (metrics, connect)...
        assert SECRET_ENDPOINT not in caplog.text
        assert SECRET_KEY_PATH not in caplog.text
        assert "certs/" not in caplog.text


class TestMetrics:
    def test_metrics_logged_periodically_and_at_close(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        publisher = make_publisher(FakeBroker(), metrics_interval_s=0.0)
        with caplog.at_level(logging.INFO):
            publisher.publish(make_payload(seq=0))
            publisher.publish(make_payload(seq=1))
            publisher.close()
        metric_lines = [line for line in caplog.text.splitlines() if "mqtt metrics" in line]
        assert len(metric_lines) >= 3  # two periodic + one final
        assert "mqtt metrics (final): sent=2 failed=0 retries=0" in caplog.text


class TestSettings:
    def test_settings_read_from_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PYROSENSE_IOT_ENDPOINT", "example-ats.iot.us-east-1.amazonaws.com")
        monkeypatch.setenv("PYROSENSE_CERT_PATH", "certs/device.pem.crt")
        monkeypatch.setenv("PYROSENSE_PRIVATE_KEY_PATH", "certs/private.pem.key")
        monkeypatch.setenv("PYROSENSE_ROOT_CA_PATH", "certs/AmazonRootCA1.pem")
        monkeypatch.setenv("PYROSENSE_ENV", "staging")

        settings = MqttSettings(_env_file=None)
        assert settings.iot_endpoint == "example-ats.iot.us-east-1.amazonaws.com"
        assert settings.env == "staging"
        assert settings.topic_base == "pyrosense"  # default

    def test_missing_environment_fails_early(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for name in (
            "PYROSENSE_IOT_ENDPOINT",
            "PYROSENSE_CERT_PATH",
            "PYROSENSE_PRIVATE_KEY_PATH",
            "PYROSENSE_ROOT_CA_PATH",
        ):
            monkeypatch.delenv(name, raising=False)
        with pytest.raises(Exception, match="iot_endpoint"):
            MqttSettings(_env_file=None)
