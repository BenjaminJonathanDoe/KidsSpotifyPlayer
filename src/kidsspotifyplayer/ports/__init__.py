"""Application port interfaces for KidsSpotifyPlayer."""

from .audio_output import AudioOutput
from .button_input import ButtonInput
from .config_repository import ConfigRepository
from .feedback_output import FeedbackOutput
from .nfc_reader import NfcReader
from .spotify_player import SpotifyPlayer

__all__ = [
    "AudioOutput",
    "ButtonInput",
    "ConfigRepository",
    "FeedbackOutput",
    "NfcReader",
    "SpotifyPlayer",
]
