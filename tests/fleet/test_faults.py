"""Tests for the FaultInjector: every fault, composability, contract validity."""

from datetime import UTC, datetime, timedelta

from pyrosense_sim.contracts.telemetry import DeviceStatus, TelemetryPayload
from pyrosense_sim.fleet.config import (
    BatteryDecayConfig,
    BurstReconnectConfig,
    DuplicatesConfig,
    FaultsConfig,
    NodeDropoutConfig,
    OutOfOrderConfig,
)
from pyrosense_sim.fleet.faults import FaultInjector
from pyrosense_sim.publishers.base import Publisher

START = datetime(2026, 1, 15, tzinfo=UTC)


class RecordingPublisher:
    """Test double: records everything, tracks close()."""

    def __init__(self) -> None:
        self.payloads: list[TelemetryPayload] = []
        self.closed = False

    def publish(self, payload: TelemetryPayload) -> None:
        self.payloads.append(payload)

    def close(self) -> None:
        self.closed = True


def make_payload(
    device_id: str = "PYRO-T1-0001",
    seq: int = 0,
    t_s: float = 0.0,
    gateway_id: str = "GW-01",
    battery_pct: float = 100.0,
) -> TelemetryPayload:
    return TelemetryPayload(
        device_id=device_id,
        gateway_id=gateway_id,
        ts_device=START + timedelta(seconds=t_s),
        seq=seq,
        lat=4.55,
        lon=-74.05,
        elevation_m=2800.0,
        temp_c=15.0,
        rh_pct=80.0,
        smoke_ppm=0.02,
        wind_speed_ms=None,
        wind_dir_deg=None,
        battery_pct=battery_pct,
        status=DeviceStatus.OK,
    )


def make_injector(inner: RecordingPublisher, config: FaultsConfig, seed: int = 1) -> FaultInjector:
    return FaultInjector(inner, config, start_time=START, seed=seed)


def test_satisfies_publisher_protocol() -> None:
    injector = make_injector(RecordingPublisher(), FaultsConfig())
    assert isinstance(injector, Publisher)


def test_no_faults_configured_is_a_transparent_passthrough() -> None:
    inner = RecordingPublisher()
    injector = make_injector(inner, FaultsConfig())
    payload = make_payload()
    injector.publish(payload)
    injector.close()
    assert inner.payloads == [payload]
    assert inner.closed


class TestNodeDropout:
    CONFIG = FaultsConfig(
        node_dropout=NodeDropoutConfig(fraction=1.0, period_min=60.0, window_min=10.0)
    )

    def test_member_is_silent_inside_the_window_only(self) -> None:
        inner = RecordingPublisher()
        injector = make_injector(inner, self.CONFIG)
        injector.publish(make_payload(seq=0, t_s=5 * 60.0))  # minute 5: silent window
        injector.publish(make_payload(seq=1, t_s=30 * 60.0))  # minute 30: talking
        injector.publish(make_payload(seq=2, t_s=65 * 60.0))  # next period, minute 5: silent
        assert [payload.seq for payload in inner.payloads] == [1]

    def test_fraction_selects_a_subset_of_devices(self) -> None:
        inner = RecordingPublisher()
        config = FaultsConfig(
            node_dropout=NodeDropoutConfig(fraction=0.5, period_min=60.0, window_min=60.0)
        )
        injector = make_injector(inner, config, seed=7)
        device_ids = [f"PYRO-T1-{index:04d}" for index in range(1, 41)]
        for device_id in device_ids:
            injector.publish(make_payload(device_id=device_id, t_s=60.0))
        survivors = {payload.device_id for payload in inner.payloads}
        assert 0 < len(survivors) < len(device_ids)  # some silenced, not all


class TestBurstReconnect:
    CONFIG = FaultsConfig(
        burst_reconnect=BurstReconnectConfig(
            gateway_id="GW-01", offline_from_hour=1.0, offline_hours=2.0
        )
    )

    def test_backlog_replays_with_original_old_timestamps(self) -> None:
        inner = RecordingPublisher()
        injector = make_injector(inner, self.CONFIG)
        # Online before the window.
        injector.publish(make_payload(seq=0, t_s=1800.0))
        # Offline window [1h, 3h): these get buffered.
        offline_times = [3600.0 * 1.5, 3600.0 * 2.0, 3600.0 * 2.5]
        for seq, t_s in enumerate(offline_times, start=1):
            injector.publish(make_payload(seq=seq, t_s=t_s))
        assert [payload.seq for payload in inner.payloads] == [0]
        # First payload after the window triggers the burst.
        injector.publish(make_payload(seq=4, t_s=3600.0 * 3.1))

        seqs = [payload.seq for payload in inner.payloads]
        assert seqs == [0, 1, 2, 3, 4]  # backlog first, consecutive seq
        replayed = inner.payloads[1:4]
        reconnect_ts = inner.payloads[4].ts_device
        # Original (old) timestamps preserved: all strictly before reconnection.
        assert [p.ts_device for p in replayed] == [
            START + timedelta(seconds=t) for t in offline_times
        ]
        assert all(p.ts_device < reconnect_ts for p in replayed)

    def test_other_gateways_are_unaffected(self) -> None:
        inner = RecordingPublisher()
        injector = make_injector(inner, self.CONFIG)
        injector.publish(make_payload(gateway_id="GW-02", t_s=3600.0 * 1.5))
        assert len(inner.payloads) == 1

    def test_unflushed_backlog_is_lost_on_close_not_leaked(self) -> None:
        inner = RecordingPublisher()
        injector = make_injector(inner, self.CONFIG)
        injector.publish(make_payload(seq=0, t_s=3600.0 * 1.5))  # buffered forever
        injector.close()
        assert inner.payloads == []
        assert inner.closed


class TestDuplicates:
    def test_probability_one_duplicates_every_payload(self) -> None:
        inner = RecordingPublisher()
        config = FaultsConfig(duplicates=DuplicatesConfig(probability=1.0))
        injector = make_injector(inner, config)
        injector.publish(make_payload(seq=7))
        assert len(inner.payloads) == 2
        assert inner.payloads[0].device_id == inner.payloads[1].device_id
        assert inner.payloads[0].seq == inner.payloads[1].seq == 7


class TestOutOfOrder:
    def test_local_permutation_preserves_the_multiset(self) -> None:
        inner = RecordingPublisher()
        config = FaultsConfig(out_of_order=OutOfOrderConfig(window=4))
        injector = make_injector(inner, config, seed=3)
        for seq in range(8):
            injector.publish(make_payload(seq=seq, t_s=60.0 * seq))
        injector.close()

        seqs = [payload.seq for payload in inner.payloads]
        assert sorted(seqs) == list(range(8))  # nothing lost, nothing invented
        assert seqs != list(range(8))  # but the order changed locally

    def test_close_flushes_a_partial_window(self) -> None:
        inner = RecordingPublisher()
        config = FaultsConfig(out_of_order=OutOfOrderConfig(window=10))
        injector = make_injector(inner, config)
        injector.publish(make_payload(seq=0))
        injector.publish(make_payload(seq=1))
        injector.close()
        assert sorted(payload.seq for payload in inner.payloads) == [0, 1]
        assert inner.closed


class TestBatteryDecay:
    CONFIG = FaultsConfig(battery_decay=BatteryDecayConfig(extra_pct_per_day=2400.0))

    def test_rewrites_battery_and_status_over_time(self) -> None:
        inner = RecordingPublisher()
        injector = make_injector(inner, self.CONFIG)
        injector.publish(make_payload(seq=0, t_s=0.0))  # no elapsed time
        injector.publish(make_payload(seq=1, t_s=3600.0 * 0.85))  # -85% -> 15 left
        injector.publish(make_payload(seq=2, t_s=3600.0))  # -100% -> 0 left

        assert inner.payloads[0].status is DeviceStatus.OK
        assert inner.payloads[1].status is DeviceStatus.LOW_BATTERY
        assert inner.payloads[2].status is DeviceStatus.DEGRADED
        assert inner.payloads[2].battery_pct == 0.0

    def test_rewritten_payloads_still_validate_against_v1(self) -> None:
        inner = RecordingPublisher()
        injector = make_injector(inner, self.CONFIG)
        injector.publish(make_payload(t_s=3600.0 * 5))  # way past empty battery
        for payload in inner.payloads:
            TelemetryPayload.model_validate(payload.model_dump())  # raises if invalid


class TestComposability:
    def test_injectors_stack_over_each_other(self) -> None:
        inner = RecordingPublisher()
        duplicating = make_injector(
            inner, FaultsConfig(duplicates=DuplicatesConfig(probability=1.0))
        )
        decaying = FaultInjector(
            duplicating,
            FaultsConfig(battery_decay=BatteryDecayConfig(extra_pct_per_day=2400.0)),
            start_time=START,
            seed=2,
        )
        decaying.publish(make_payload(t_s=3600.0))
        decaying.close()
        assert len(inner.payloads) == 2  # duplicated after decay
        assert all(payload.battery_pct == 0.0 for payload in inner.payloads)
        assert inner.closed
