from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kidsspotifyplayer.health import (
    HealthMonitor,
    HealthRegistry,
    HealthStatus,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_stale_critical_heartbeat_is_detected_with_fake_time() -> None:
    clock = FakeClock()
    registry = HealthRegistry(monotonic=clock.monotonic)
    registry.register("nfc_reader", stale_after_seconds=2.0)

    clock.advance(2.1)
    failures = registry.check_stale()

    assert [failure.name for failure in failures] == ["nfc_reader"]
    assert failures[0].status is HealthStatus.UNHEALTHY
    assert failures[0].last_error == "heartbeat stale"
    assert registry.fatal_event.is_set()


def test_healthy_component_is_not_failed_by_long_idle_when_heartbeating() -> None:
    clock = FakeClock()
    registry = HealthRegistry(monotonic=clock.monotonic)
    registry.register("nfc_reader", stale_after_seconds=2.0)

    for _ in range(700):
        clock.advance(2.0)
        registry.heartbeat("nfc_reader")
        assert registry.check_stale() == []

    assert clock.now > 20 * 60
    assert not registry.fatal_event.is_set()


def test_health_monitor_shutdown_is_bounded_even_with_long_poll_interval() -> None:
    registry = HealthRegistry()
    monitor = HealthMonitor(registry, check_interval_seconds=3600.0)
    monitor.start()

    monitor.stop(timeout_seconds=0.5)

    assert monitor._thread is None


def test_health_monitor_failure_signals_fatal_runtime_shutdown() -> None:
    class FailingHealthMonitor(HealthMonitor):
        def check_once(self) -> list[object]:
            raise RuntimeError("health check failed")

    registry = HealthRegistry()
    monitor = FailingHealthMonitor(
        registry,
        check_interval_seconds=0.001,
    )

    monitor.start()
    assert registry.fatal_event.wait(timeout=1.0)
    monitor.stop()

    health = registry.snapshot()["health_monitor"]
    assert health.status is HealthStatus.UNHEALTHY
    assert "health check failed" in (health.last_error or "")
