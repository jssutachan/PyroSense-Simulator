"""MQTT publisher toward AWS IoT Core (mutual TLS, QoS 1).

Configuration comes from the environment / ``.env`` (see
``.env.example``) via pydantic-settings — endpoint, certificate paths
and topic base are NEVER hardcoded, and none of them is ever logged.

Topic layout: ``{topic_base}/{env}/telemetry/{device_id}`` at **QoS 1**
(at-least-once). Direct consequence (ADR-0013): the broker may deliver
duplicates, so **deduplication by ``device_id`` + ``seq`` is the
cloud's responsibility** — the simulator will not pretend the network
is exactly-once.

Failed publishes retry with exponential backoff plus jitter; a payload
that exhausts its retries is dropped and counted (the load test keeps
running). Publication metrics (sent, failed, retries) are logged every
``metrics_interval_s`` seconds and at close.

The AWS transport itself (`awsiot` connection) is isolated behind the
tiny :class:`MqttConnection` protocol so every behavior above is tested
against a mocked broker; real IoT Core usage is deferred until the
cloud stage (E2) exists.
"""

import logging
import random
import time
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from pydantic_settings import BaseSettings, SettingsConfigDict

from pyrosense_sim.contracts.telemetry import TelemetryPayload

logger = logging.getLogger(__name__)

QOS_AT_LEAST_ONCE = 1


class MqttSettings(BaseSettings):
    """IoT Core connection settings, read from env vars / ``.env``.

    Env names carry the ``PYROSENSE_`` prefix: ``PYROSENSE_IOT_ENDPOINT``,
    ``PYROSENSE_CERT_PATH``, ``PYROSENSE_PRIVATE_KEY_PATH``,
    ``PYROSENSE_ROOT_CA_PATH``, ``PYROSENSE_TOPIC_BASE``, ``PYROSENSE_ENV``.
    """

    model_config = SettingsConfigDict(env_prefix="PYROSENSE_", env_file=".env", extra="ignore")

    iot_endpoint: str
    cert_path: Path
    private_key_path: Path
    root_ca_path: Path
    topic_base: str = "pyrosense"
    env: str = "dev"
    client_id: str = "pyrosense-fleet-sim"


class MqttConnection(Protocol):
    """Minimal broker interface; the AWS implementation and mocks satisfy it."""

    def connect(self) -> None:
        """Open the connection. Raises on failure."""
        ...

    def publish(self, topic: str, payload: bytes, qos: int) -> None:
        """Publish one message, blocking until acked. Raises on failure."""
        ...

    def disconnect(self) -> None:
        """Close the connection (best effort)."""
        ...


class MqttPublisher:
    """Publishes telemetry to AWS IoT Core with retries and metrics."""

    def __init__(
        self,
        settings: MqttSettings | None = None,
        *,
        connection: MqttConnection | None = None,
        max_retries: int = 5,
        base_backoff_s: float = 0.5,
        max_backoff_s: float = 30.0,
        metrics_interval_s: float = 30.0,
        rng: random.Random | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        """Configure the publisher.

        Args:
            settings: Connection settings; read from the environment when
                omitted.
            connection: Broker override (tests inject a mock). Defaults to
                the real AWS IoT connection built from ``settings``.
            max_retries: Retries per payload before dropping it.
            base_backoff_s: First backoff delay; doubles per attempt.
            max_backoff_s: Backoff ceiling before jitter.
            metrics_interval_s: How often to log publication metrics.
            rng: Source for the backoff jitter (injectable for tests).
            sleep_fn: Pacing function (tests use a no-op).

        Raises:
            pydantic.ValidationError: If settings are omitted and the
                required environment variables are missing.
        """
        self._settings = settings if settings is not None else MqttSettings()
        self._connection = (
            connection if connection is not None else _build_aws_connection(self._settings)
        )
        self._max_retries = max_retries
        self._base_backoff_s = base_backoff_s
        self._max_backoff_s = max_backoff_s
        self._metrics_interval_s = metrics_interval_s
        self._rng = rng if rng is not None else random.Random()
        self._sleep = sleep_fn
        self._connected = False
        self._sent = 0
        self._failed = 0
        self._retries = 0
        self._last_metrics_at = time.monotonic()

    def publish(self, payload: TelemetryPayload) -> None:
        """Publish one payload at QoS 1, retrying with backoff + jitter.

        A payload that exhausts its retries is dropped and counted as
        failed — the run continues. No secret (endpoint, cert or key
        paths/contents) is ever logged.

        Args:
            payload: Contract-valid payload to send.
        """
        topic = f"{self._settings.topic_base}/{self._settings.env}/telemetry/{payload.device_id}"
        body = payload.model_dump_json().encode("utf-8")
        for attempt in range(self._max_retries + 1):
            try:
                self._ensure_connected()
                self._connection.publish(topic, body, QOS_AT_LEAST_ONCE)
                self._sent += 1
                break
            except Exception:  # transport boundary: awscrt raises varied exception types
                self._connected = False  # force reconnect on the next attempt
                if attempt == self._max_retries:
                    self._failed += 1
                    logger.warning(
                        "publish failed after %d retries: device=%s seq=%d (payload dropped)",
                        self._max_retries,
                        payload.device_id,
                        payload.seq,
                    )
                else:
                    self._retries += 1
                    self._sleep(self._backoff_delay(attempt))
        self._maybe_log_metrics()

    def close(self) -> None:
        """Log final metrics and disconnect (best effort)."""
        self._log_metrics(final=True)
        if self._connected:
            self._connection.disconnect()
            self._connected = False

    def _ensure_connected(self) -> None:
        if not self._connected:
            self._connection.connect()
            self._connected = True
            logger.info("mqtt connected (client_id=%s)", self._settings.client_id)

    def _backoff_delay(self, attempt: int) -> float:
        delay = min(self._max_backoff_s, self._base_backoff_s * (2.0**attempt))
        return delay + self._rng.uniform(0.0, self._base_backoff_s)

    def _maybe_log_metrics(self) -> None:
        now = time.monotonic()
        if now - self._last_metrics_at >= self._metrics_interval_s:
            self._last_metrics_at = now
            self._log_metrics(final=False)

    def _log_metrics(self, *, final: bool) -> None:
        logger.info(
            "mqtt metrics%s: sent=%d failed=%d retries=%d",
            " (final)" if final else "",
            self._sent,
            self._failed,
            self._retries,
        )


def _build_aws_connection(settings: MqttSettings) -> MqttConnection:  # pragma: no cover
    """Build the real AWS IoT Core connection (exercised only against AWS, E2 stage)."""
    return _AwsIotConnection(settings)


class _AwsIotConnection:  # pragma: no cover - thin wrapper over awsiotsdk, needs real AWS
    """Mutual-TLS connection to AWS IoT Core via awsiotsdk."""

    _TIMEOUT_S = 10.0

    def __init__(self, settings: MqttSettings) -> None:
        self._settings = settings
        self._connection: object | None = None

    def connect(self) -> None:
        from awscrt import mqtt
        from awsiot import mqtt_connection_builder

        connection = mqtt_connection_builder.mtls_from_path(
            endpoint=self._settings.iot_endpoint,
            cert_filepath=str(self._settings.cert_path),
            pri_key_filepath=str(self._settings.private_key_path),
            ca_filepath=str(self._settings.root_ca_path),
            client_id=self._settings.client_id,
            clean_session=False,
            keep_alive_secs=30,
        )
        connection.connect().result(self._TIMEOUT_S)
        self._mqtt = mqtt
        self._connection = connection

    def publish(self, topic: str, payload: bytes, qos: int) -> None:
        assert self._connection is not None  # connect() runs first by construction
        future, _packet_id = self._connection.publish(  # type: ignore[attr-defined]
            topic=topic,
            payload=payload,
            qos=self._mqtt.QoS(qos),
        )
        future.result(self._TIMEOUT_S)

    def disconnect(self) -> None:
        if self._connection is not None:
            self._connection.disconnect().result(self._TIMEOUT_S)  # type: ignore[attr-defined]
            self._connection = None
