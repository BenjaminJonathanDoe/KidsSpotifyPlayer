from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from kidsspotifyplayer.adapters.raspberry_pi.pn532_nfc_reader import (
    Pn532NfcReader,
)
from kidsspotifyplayer.domain.events import NfcCardDetected
from kidsspotifyplayer.ports import NfcReader


class RecordingCoordinator:
    def __init__(self, publish_results: list[bool] | None = None) -> None:
        self.events: list[NfcCardDetected] = []
        self.publish_results = list(publish_results or [True])

    def publish(self, event: NfcCardDetected) -> bool:
        self.events.append(event)

        if self.publish_results:
            return self.publish_results.pop(0)

        return True


class FakePn532Client:
    def __init__(
        self,
        responses: list[bytes | bytearray | None] | None = None,
    ) -> None:
        self.responses = list(responses or [])
        self.calls: list[float] = []
        self.exception: Exception | None = None

    def read_passive_target(
        self,
        *,
        timeout: float,
    ) -> bytes | bytearray | None:
        self.calls.append(timeout)

        if self.exception is not None:
            raise self.exception

        if not self.responses:
            return None

        return self.responses.pop(0)


class BlockingPn532Client(FakePn532Client):
    """Block a read until the test explicitly releases it."""

    def __init__(self) -> None:
        super().__init__()
        self.started = threading.Event()
        self.release = threading.Event()

    def read_passive_target(
        self,
        *,
        timeout: float,
    ) -> bytes | bytearray | None:
        self.calls.append(timeout)
        self.started.set()
        self.release.wait()
        return None


def test_adapter_structurally_satisfies_nfc_reader_protocol() -> None:
    adapter = Pn532NfcReader(
        FakePn532Client(),
        RecordingCoordinator(),
    )

    assert isinstance(adapter, NfcReader)


@pytest.mark.parametrize(
    ("timeout", "match"),
    [
        (0, "read_timeout_seconds"),
        (True, "read_timeout_seconds"),
        (-0.1, "read_timeout_seconds"),
        ("0.2", "read_timeout_seconds"),
    ],
)
def test_constructor_rejects_invalid_timeout_values(
    timeout: object,
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        Pn532NfcReader(
            FakePn532Client(),
            RecordingCoordinator(),
            read_timeout_seconds=timeout,
        )


@pytest.mark.parametrize(
    ("count", "match"),
    [
        (0, "absent_reads_to_rearm"),
        (True, "absent_reads_to_rearm"),
        (0.5, "absent_reads_to_rearm"),
        ("2", "absent_reads_to_rearm"),
    ],
)
def test_constructor_rejects_invalid_absent_read_counts(
    count: object,
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        Pn532NfcReader(
            FakePn532Client(),
            RecordingCoordinator(),
            absent_reads_to_rearm=count,
        )


def test_uid_bytes_are_formatted_as_uppercase_hex_without_separators() -> None:
    adapter = Pn532NfcReader(
        FakePn532Client(),
        RecordingCoordinator(),
    )

    assert adapter._format_uid(
        bytes([0x04, 0xA1, 0x0B, 0xFF])
    ) == "04A10BFF"

    assert adapter._format_uid(
        bytearray([0x01, 0x02])
    ) == "0102"


def test_first_card_read_publishes_one_event() -> None:
    coordinator = RecordingCoordinator()
    adapter = Pn532NfcReader(
        FakePn532Client(
            [
                bytes([0x04, 0xA1, 0x0B, 0xFF]),
            ]
        ),
        coordinator,
    )

    adapter._poll_once()

    assert coordinator.events == [
        NfcCardDetected(card_id="04A10BFF"),
    ]


def test_repeated_reads_of_same_present_card_publish_only_once() -> None:
    card_uid = bytes([0x04, 0xA1, 0x0B, 0xFF])
    coordinator = RecordingCoordinator()
    adapter = Pn532NfcReader(
        FakePn532Client([card_uid, card_uid]),
        coordinator,
    )

    adapter._poll_once()
    adapter._poll_once()

    assert coordinator.events == [
        NfcCardDetected(card_id="04A10BFF"),
    ]


def test_card_removal_publishes_no_event() -> None:
    coordinator = RecordingCoordinator()
    adapter = Pn532NfcReader(
        FakePn532Client(
            [
                bytes([0x04, 0xA1, 0x0B, 0xFF]),
                None,
                None,
            ]
        ),
        coordinator,
        absent_reads_to_rearm=2,
    )

    adapter._poll_once()
    adapter._poll_once()
    adapter._poll_once()

    assert coordinator.events == [
        NfcCardDetected(card_id="04A10BFF"),
    ]


def test_same_card_publishes_again_after_absence_threshold() -> None:
    card_uid = bytes([0x04, 0xA1, 0x0B, 0xFF])
    coordinator = RecordingCoordinator()
    adapter = Pn532NfcReader(
        FakePn532Client(
            [
                card_uid,
                None,
                None,
                card_uid,
            ]
        ),
        coordinator,
        absent_reads_to_rearm=2,
    )

    adapter._poll_once()
    adapter._poll_once()
    adapter._poll_once()
    adapter._poll_once()

    assert coordinator.events == [
        NfcCardDetected(card_id="04A10BFF"),
        NfcCardDetected(card_id="04A10BFF"),
    ]


def test_different_card_publishes_immediately_without_empty_read() -> None:
    coordinator = RecordingCoordinator()
    adapter = Pn532NfcReader(
        FakePn532Client(
            [
                bytes([0x04, 0xA1, 0x0B, 0xFF]),
                bytes([0x01, 0x02]),
            ]
        ),
        coordinator,
    )

    adapter._poll_once()
    adapter._poll_once()

    assert coordinator.events == [
        NfcCardDetected(card_id="04A10BFF"),
        NfcCardDetected(card_id="0102"),
    ]


def test_publish_false_does_not_repeat_while_card_remains_present() -> None:
    card_uid = bytes([0x04, 0xA1, 0x0B, 0xFF])
    coordinator = RecordingCoordinator([False])
    adapter = Pn532NfcReader(
        FakePn532Client([card_uid, card_uid]),
        coordinator,
    )

    adapter._poll_once()
    adapter._poll_once()

    assert coordinator.events == [
        NfcCardDetected(card_id="04A10BFF"),
    ]


def test_start_returns_without_blocking() -> None:
    adapter = Pn532NfcReader(
        FakePn532Client(),
        RecordingCoordinator(),
    )

    adapter.start()

    assert adapter._thread is not None

    adapter.stop()


def test_start_is_idempotent() -> None:
    client = BlockingPn532Client()
    adapter = Pn532NfcReader(
        client,
        RecordingCoordinator(),
    )

    adapter.start()
    assert client.started.wait(timeout=1.0)

    first_thread = adapter._thread
    adapter.start()

    assert adapter._thread is first_thread
    assert len(client.calls) == 1

    client.release.set()
    adapter.stop()


def test_stop_stops_and_joins_worker() -> None:
    adapter = Pn532NfcReader(
        FakePn532Client(),
        RecordingCoordinator(),
    )
    adapter.start()

    adapter.stop()

    assert adapter._thread is None


def test_stop_is_idempotent_after_successful_stop() -> None:
    adapter = Pn532NfcReader(
        FakePn532Client(),
        RecordingCoordinator(),
    )

    adapter.start()
    adapter.stop()
    adapter.stop()

    assert adapter._thread is None


def test_stop_keeps_thread_ownership_until_worker_exits() -> None:
    client = BlockingPn532Client()
    adapter = Pn532NfcReader(
        client,
        RecordingCoordinator(),
    )
    adapter.start()

    assert client.started.wait(timeout=1.0)

    worker = adapter._thread
    assert worker is not None

    stop_finished = threading.Event()
    stop_error: list[BaseException] = []

    def stop_adapter() -> None:
        try:
            adapter.stop()
        except BaseException as error:
            stop_error.append(error)
        finally:
            stop_finished.set()

    stopping_thread = threading.Thread(target=stop_adapter)
    stopping_thread.start()

    # Ensure stop() has entered its waiting phase.
    assert adapter._stop_event.wait(timeout=1.0)

    assert adapter._thread is worker
    assert worker.is_alive()
    assert not stop_finished.is_set()

    client.release.set()
    stopping_thread.join(timeout=1.0)

    assert not stopping_thread.is_alive()
    assert stop_finished.is_set()
    assert stop_error == []
    assert adapter._thread is None


def test_stop_timeout_retains_worker_and_prevents_replacement() -> None:
    client = BlockingPn532Client()
    adapter = Pn532NfcReader(
        client,
        RecordingCoordinator(),
        read_timeout_seconds=0.01,
    )
    adapter.start()

    assert client.started.wait(timeout=1.0)

    original_thread = adapter._thread
    assert original_thread is not None

    with pytest.raises(RuntimeError, match="did not stop"):
        adapter.stop()

    assert adapter._thread is original_thread
    assert original_thread.is_alive()

    # A second worker must not be created while the first one is alive.
    adapter.start()

    assert adapter._thread is original_thread
    assert len(client.calls) == 1

    # Release the blocked hardware call and clean up the worker.
    client.release.set()
    adapter.stop()

    assert adapter._thread is None
    assert not original_thread.is_alive()


def test_hardware_client_exceptions_are_not_converted_into_absence() -> None:
    client = FakePn532Client()
    client.exception = RuntimeError("boom")
    adapter = Pn532NfcReader(
        client,
        RecordingCoordinator(),
    )

    with pytest.raises(RuntimeError, match="boom"):
        adapter._poll_once()


def test_adapter_uses_injected_client_without_real_hardware() -> None:
    client = FakePn532Client()
    adapter = Pn532NfcReader(
        client,
        RecordingCoordinator(),
    )

    assert adapter._client is client