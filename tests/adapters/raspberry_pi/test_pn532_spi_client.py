from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from kidsspotifyplayer.adapters.raspberry_pi.pn532_spi_client import (
    Pn532SpiClient,
)


class FakePn532Device:
    def __init__(
        self,
        response: bytes | bytearray | None,
    ) -> None:
        self.response = response
        self.calls: list[tuple[str, object]] = []

    def SAM_configuration(self) -> None:
        self.calls.append(("SAM_configuration", None))

    def read_passive_target(
        self,
        *,
        timeout: float,
    ) -> bytes | bytearray | None:
        self.calls.append(("read_passive_target", timeout))
        return self.response


def test_spi_client_initializes_device_and_returns_uid_bytes() -> None:
    device = FakePn532Device(
        bytes([0x04, 0xA1, 0x0B, 0xFF]),
    )
    client = Pn532SpiClient(device=device)

    assert client.read_passive_target(
        timeout=0.2
    ) == bytes([0x04, 0xA1, 0x0B, 0xFF])

    assert device.calls[0] == (
        "SAM_configuration",
        None,
    )
    assert device.calls[1] == (
        "read_passive_target",
        0.2,
    )