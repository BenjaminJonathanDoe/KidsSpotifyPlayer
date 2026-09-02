from __future__ import annotations

import threading
from typing import Protocol, runtime_checkable

from kidsspotifyplayer.domain.events import NfcCardDetected
from kidsspotifyplayer.health import HealthRegistry
from kidsspotifyplayer.input.coordinator import InputCoordinator


@runtime_checkable
class Pn532Client(Protocol):
    def read_passive_target(self, *, timeout: float) -> bytes | bytearray | None:
        ...


class Pn532NfcReader:
    def __init__(
        self,
        client: Pn532Client,
        input_coordinator: InputCoordinator,
        *,
        read_timeout_seconds: float = 0.2,
        absent_reads_to_rearm: int = 2,
        health_registry: HealthRegistry | None = None,
    ) -> None:
        self._validate_constructor_args(read_timeout_seconds, absent_reads_to_rearm)
        self._client = client
        self._input_coordinator = input_coordinator
        self._read_timeout_seconds = read_timeout_seconds
        self._absent_reads_to_rearm = absent_reads_to_rearm
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._armed = True
        self._present_card_id: str | None = None
        self._absence_count = 0
        self._thread_lock = threading.Lock()
        self._health_registry = health_registry
        if health_registry is not None:
            health_registry.register(
                "nfc_reader",
                stale_after_seconds=5.0,
            )
            health_registry.register(
                "pn532_hardware",
                stale_after_seconds=5.0,
            )

    def start(self) -> None:
        with self._thread_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._thread_lock:
            thread = self._thread
            if thread is None:
                return

            self._stop_event.set()

        thread.join(timeout=self._read_timeout_seconds + 1.0)

        if thread.is_alive():
            raise RuntimeError("PN532 reader thread did not stop")

        with self._thread_lock:
            if self._thread is thread:
                self._thread = None

    def _run(self) -> None:
        try:
            while not self._stop_event.is_set():
                self._poll_once()
        except Exception as error:
            if not self._fatal_shutdown_signaled():
                self._mark_unhealthy(
                    "nfc_reader",
                    f"worker thread terminated: {type(error).__name__}: {error}",
                )

    def _poll_once(self) -> None:
        try:
            uid = self._client.read_passive_target(timeout=self._read_timeout_seconds)
        except Exception as error:
            self._mark_unhealthy(
                "pn532_hardware",
                f"{type(error).__name__}: {error}",
            )
            raise

        self._heartbeat("pn532_hardware", operation_succeeded=True)
        if uid is None:
            self._handle_absence()
            self._heartbeat("nfc_reader")
            return

        card_id = self._format_uid(uid)
        if not self._armed and self._present_card_id == card_id:
            self._absence_count = 0
            self._heartbeat("nfc_reader")
            return

        self._publish_card(card_id)
        self._present_card_id = card_id
        self._absence_count = 0
        self._armed = False
        self._heartbeat("nfc_reader", operation_succeeded=True)

    def _heartbeat(self, component: str, *, operation_succeeded: bool = False) -> None:
        if self._health_registry is not None:
            self._health_registry.heartbeat(
                component,
                operation_succeeded=operation_succeeded,
            )

    def _mark_unhealthy(self, component: str, reason: str) -> None:
        if self._health_registry is not None:
            self._health_registry.unhealthy(component, reason)

    def _fatal_shutdown_signaled(self) -> bool:
        return (
            self._health_registry is not None
            and self._health_registry.fatal_event.is_set()
        )

    def _handle_absence(self) -> None:
        self._absence_count += 1
        if self._absence_count >= self._absent_reads_to_rearm:
            self._present_card_id = None
            self._armed = True
            self._absence_count = 0

    def _publish_card(self, card_id: str) -> None:
        self._input_coordinator.publish(NfcCardDetected(card_id=card_id))

    def _format_uid(self, uid: bytes | bytearray) -> str:
        return "".join(f"{byte:02X}" for byte in uid)

    @staticmethod
    def _validate_constructor_args(read_timeout_seconds: float, absent_reads_to_rearm: int) -> None:
        if isinstance(read_timeout_seconds, bool) or not isinstance(read_timeout_seconds, (int, float)):
            raise ValueError("read_timeout_seconds must be a real number")
        if read_timeout_seconds <= 0:
            raise ValueError("read_timeout_seconds must be greater than zero")
        if isinstance(absent_reads_to_rearm, bool) or not isinstance(absent_reads_to_rearm, int):
            raise ValueError("absent_reads_to_rearm must be an integer")
        if absent_reads_to_rearm <= 0:
            raise ValueError("absent_reads_to_rearm must be greater than zero")
