from __future__ import annotations

import threading
from typing import Protocol, runtime_checkable

from kidsspotifyplayer.domain.events import NfcCardDetected
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
        while not self._stop_event.is_set():
            self._poll_once()

    def _poll_once(self) -> None:
        uid = self._client.read_passive_target(timeout=self._read_timeout_seconds)
        if uid is None:
            self._handle_absence()
            return

        card_id = self._format_uid(uid)
        if not self._armed and self._present_card_id == card_id:
            self._absence_count = 0
            return

        self._publish_card(card_id)
        self._present_card_id = card_id
        self._absence_count = 0
        self._armed = False

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
