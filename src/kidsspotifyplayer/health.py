from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Callable


class HealthStatus(Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


@dataclass(frozen=True)
class ComponentHealth:
    name: str
    status: HealthStatus
    last_heartbeat: float
    last_successful_operation: float | None = None
    last_error: str | None = None
    details: dict[str, Any] | None = None
    critical: bool = True
    stale_after_seconds: float | None = None


class HealthRegistry:
    def __init__(self, *, monotonic: Callable[[], float] | None = None) -> None:
        self._monotonic = monotonic or time.monotonic
        self._logger = logging.getLogger(__name__)
        self._components: dict[str, ComponentHealth] = {}
        self._lock = threading.Lock()
        self._fatal_event = threading.Event()

    @property
    def fatal_event(self) -> threading.Event:
        return self._fatal_event

    def register(
        self,
        name: str,
        *,
        critical: bool = True,
        stale_after_seconds: float | None = None,
    ) -> None:
        now = self._monotonic()
        with self._lock:
            self._components.setdefault(
                name,
                ComponentHealth(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    last_heartbeat=now,
                    critical=critical,
                    stale_after_seconds=stale_after_seconds,
                ),
            )

    def heartbeat(self, name: str, *, operation_succeeded: bool = False) -> None:
        now = self._monotonic()
        with self._lock:
            current = self._require(name)
            if current.status is HealthStatus.UNHEALTHY:
                return
            self._components[name] = replace(
                current,
                status=HealthStatus.HEALTHY,
                last_heartbeat=now,
                last_successful_operation=(
                    now if operation_succeeded else current.last_successful_operation
                ),
                last_error=None,
            )

    def unhealthy(
        self,
        name: str,
        reason: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            current = self._require(name)
            if current.status is HealthStatus.UNHEALTHY:
                return
            self._components[name] = replace(
                current,
                status=HealthStatus.UNHEALTHY,
                last_error=reason,
                details=details,
            )
            if current.critical:
                self._fatal_event.set()
        self._logger.critical(
            "component=%s status=%s reason=%r last_heartbeat_age=%.3f",
            name,
            HealthStatus.UNHEALTHY.value,
            reason,
            self.heartbeat_age(name),
        )

    def snapshot(self) -> dict[str, ComponentHealth]:
        with self._lock:
            return dict(self._components)

    def critical_failures(self) -> list[ComponentHealth]:
        with self._lock:
            return [
                component
                for component in self._components.values()
                if component.critical
                and component.status is HealthStatus.UNHEALTHY
            ]

    def heartbeat_age(self, name: str) -> float:
        with self._lock:
            component = self._require(name)
            return self._monotonic() - component.last_heartbeat

    def check_stale(self) -> list[ComponentHealth]:
        now = self._monotonic()
        stale_names: list[tuple[str, float]] = []
        with self._lock:
            for name, component in self._components.items():
                maximum_age = component.stale_after_seconds
                age = now - component.last_heartbeat
                if (
                    component.critical
                    and component.status is not HealthStatus.UNHEALTHY
                    and maximum_age is not None
                    and age > maximum_age
                ):
                    stale_names.append((name, age))

        for name, age in stale_names:
            self.unhealthy(
                name,
                "heartbeat stale",
                details={"last_heartbeat_age": age},
            )
        return self.critical_failures()

    def _require(self, name: str) -> ComponentHealth:
        try:
            return self._components[name]
        except KeyError as error:
            raise KeyError(f"health component is not registered: {name}") from error


class HealthMonitor:
    def __init__(
        self,
        registry: HealthRegistry,
        *,
        check_interval_seconds: float = 1.0,
    ) -> None:
        self._registry = registry
        self._registry.register("health_monitor")
        self._check_interval_seconds = check_interval_seconds
        self._logger = logging.getLogger(__name__)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="health-monitor",
            daemon=True,
        )
        self._thread.start()

    def check_once(self) -> list[ComponentHealth]:
        return self._registry.check_stale()

    def stop(self, *, timeout_seconds: float = 2.0) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is None:
            return
        thread.join(timeout=timeout_seconds)
        if thread.is_alive():
            raise RuntimeError("health monitor thread did not stop")
        self._thread = None

    def _run(self) -> None:
        try:
            while not self._stop_event.wait(self._check_interval_seconds):
                self.check_once()
        except Exception as error:
            reason = (
                "health monitor terminated: "
                f"{type(error).__name__}: {error}"
            )
            try:
                self._registry.unhealthy("health_monitor", reason)
            except Exception:
                self._logger.exception(
                    "component=health_monitor status=UNHEALTHY reason=%r",
                    reason,
                )
                self._registry.fatal_event.set()
