from __future__ import annotations

from typing import Any


class Pn532SpiClient:
    """Small adapter around a PN532 device object for the existing NFC reader protocol."""

    def __init__(self, *, device: Any) -> None:
        if device is None:
            raise ValueError("device must not be None")
        self._device = device
        self._initialize()

    def read_passive_target(self, *, timeout: float) -> bytes | bytearray | None:
        return self._device.read_passive_target(timeout=timeout)

    def _initialize(self) -> None:
        self._device.SAM_configuration()


def create_default_pn532_spi_client() -> Pn532SpiClient:
    import board
    import busio
    from adafruit_pn532.spi import PN532_SPI
    from digitalio import DigitalInOut

    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
    cs_pin = DigitalInOut(board.D5)
    device = PN532_SPI(spi, cs_pin, debug=False)
    return Pn532SpiClient(device=device)
