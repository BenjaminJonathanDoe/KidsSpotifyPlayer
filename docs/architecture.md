# KidsSpotifyPlayer Architecture
---
## 1. Purpose
KidsSpotifyPlayer is a child-friendly Spotify player controlled primarily through NFC cards.
```text
NFC card detected
→ resolve PlaybackTarget
→ start Spotify playback
→ continue playback after card removal
```
The NFC card is the primary MVP interface. Buttons, LEDs, displays, and battery features are later extensions.
---
## 2. Goals
The architecture must:
- isolate application logic from hardware and external services;
- remain testable without Raspberry Pi hardware;
- run efficiently on a Raspberry Pi Zero 2 W;
- support a read-only runtime filesystem;
- allow adapters to be replaced independently;
- support a future ESP32 input controller;
- serialize user input;
- discard overlapping input rather than queue it;
- fail fast on invalid startup configuration;
- preserve playback after unknown cards or recoverable input errors.
> Application logic depends on domain models and ports, never on hardware libraries, file formats, or Spotify SDKs.
---
## 3. MVP Scope
Included:
- Raspberry Pi Zero 2 W;
- PN532 NFC reader over SPI;
- JSON card-to-Spotify mapping;
- playback through one Spotify Connect device;
- NFC duplicate suppression;
- active-target suppression;
- synchronous input handling;
- finite Spotify timeouts;
- startup and shutdown wiring.
Not required:
- buttons;
- LEDs;
- display;
- runtime configuration editing;
- persistent playback state;
- queued input;
- battery monitoring;
- ESP32 communication;
- dynamic Spotify search.
---
## 4. System Overview
```text
NFC card
   ↓
PN532 over SPI
   ↓
PN532 NFC adapter
   ↓ NfcCardDetected
InputCoordinator
   ↓
EventBus
   ↓
PlayerController
   ├── ConfigRepository.find_playback_target(card_id)
   ├── ignore unknown target
   ├── ignore active target
   └── SpotifyPlayer.play_context(target)
                     ↓
             SpotifyWebApiPlayer
                     ↓
             Spotify API client
                     ↓
             Spotify Connect device
                     ↓
                    Audio
```
---
## 5. Architecture Style
The project uses Ports and Adapters architecture.
```text
External systems and hardware
            ↓
         Adapters
            ↓
           Ports
            ↓
      Application layer
            ↓
        Domain layer
```
Dependencies point inward.
- Domain represents business concepts.
- Application makes decisions and coordinates behavior.
- Ports define capabilities.
- Adapters translate hardware, storage, and external APIs.
- The composition root creates and wires objects.
---
## 6. Layers
### 6.1 Domain
Location:
```text
src/kidsspotifyplayer/domain/
```
Contains immutable events and models.
Primary model:
```python
PlaybackTarget(uri="spotify:playlist:...", name="Optional name")
```
Current input events:
- `NfcCardDetected`;
- `PlayPausePressed`;
- `NextTrackPressed`;
- `PreviousTrackPressed`;
- `VolumeUpPressed`;
- `VolumeDownPressed`.
Events describe facts and contain no behavior.
The domain must not depend on Raspberry Pi libraries, JSON, I²C, GPIO, Spotify clients, or operating-system services.
### 6.2 Application
Location:
```text
src/kidsspotifyplayer/application/
```
Current components:
- `Application`;
- `PlayerController`.
The application may depend on domain types, ports, `EventBus`, and `InputCoordinator`.
It must not depend on PN532 libraries, GPIO libraries, raw JSON, Spotify SDK response types, ALSA, or I²S details.
### 6.3 Ports
Location:
```text
src/kidsspotifyplayer/ports/
```
Current ports:
- `EventSource`;
- `NfcReader`;
- `ButtonInput`;
- `SpotifyPlayer`;
- `ConfigRepository`;
- `FeedbackOutput`;
- `AudioOutput`.
Examples:
```python
class EventSource(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
```
```python
class ConfigRepository(Protocol):
    def find_playback_target(
        self,
        card_id: str,
    ) -> PlaybackTarget | None: ...
```
```python
class SpotifyPlayer(Protocol):
    def play_context(self, target: PlaybackTarget) -> None: ...
    def toggle_play_pause(self) -> None: ...
    def next_track(self) -> None: ...
    def previous_track(self) -> None: ...
    def volume_up(self) -> None: ...
    def volume_down(self) -> None: ...
```
Ports define contracts, not production behavior.
### 6.4 Adapters
Location:
```text
src/kidsspotifyplayer/adapters/
```
Current adapters:
- `JSONConfigRepository`;
- `SpotifyWebApiPlayer`.
Planned MVP adapter:
- PN532 NFC adapter over SPI.
Rules:
- NFC hardware duplicate suppression belongs in the NFC adapter.
- JSON parsing belongs in the config adapter.
- Spotify response parsing belongs in the Spotify adapter.
- Application decisions do not belong in adapters.
### 6.5 Infrastructure
Infrastructure owns startup, dependency construction, lifecycle, signal handling, logging setup, and starting or stopping event sources.
The composition root belongs in `Application`, `bootstrap.py`, or `main.py`.
---
## 7. Repository Structure
```text
src/kidsspotifyplayer/
├── adapters/
│   ├── config/json_config_repository.py
│   ├── spotify/spotify_web_api_player.py
│   └── raspberry_pi/pn532_nfc_reader.py   # planned
├── application/
│   ├── application.py
│   └── controller.py
├── domain/
│   ├── events.py
│   └── models.py
├── event_bus/bus.py
├── input/coordinator.py
├── ports/
├── bootstrap.py                            # planned
└── main.py                                 # planned
```
---
## 8. Event Flow
The NFC adapter creates:
```python
NfcCardDetected(card_id="04A1B2C3")
```
It submits the event through:
```python
InputCoordinator.publish(event)
```
The coordinator:
1. acquires one global non-blocking lock;
2. returns `False` if another input is running;
3. publishes through the synchronous EventBus;
4. releases the lock in `finally`;
5. returns `True` after dispatch.
Discarded inputs are not queued, retried, or replayed.
```text
InputCoordinator.publish()
→ EventBus.publish()
→ PlayerController handler
→ service port call
→ handler returns
→ EventBus returns
→ InputCoordinator releases lock
```
The EventBus contains no input-specific policy.
---
## 9. PlayerController
Location:
```text
src/kidsspotifyplayer/application/controller.py
```
NFC behavior:
```text
NfcCardDetected
→ ConfigRepository.find_playback_target(card_id)
→ unknown target: report error and return
→ current target: return
→ new target: SpotifyPlayer.play_context(target)
→ remember target after success
```
The controller stores:
```python
_active_target: PlaybackTarget | None
```
The target is updated only after `play_context()` succeeds.
If playback fails or times out, the target is not remembered.
The controller does not read NFC hardware, normalize IDs, parse JSON, call Spotify APIs directly, manage locks, or start adapters.
---
## 10. NFC Architecture
### Hardware
```text
Reader: PN532
Interface: PN532 → SPI → Raspberry Pi Zero 2 W
Platform: Raspberry Pi Zero 2 W
```
Reasons:
- reliable;
- broad NFC support;
- low cost;
- mature Raspberry Pi ecosystem;
- SPI is the recommended reliable interface on Raspberry Pi.
The exact Python library remains open.
### UID normalization
```python
card_id.strip().upper()
```
Separators are preserved.
```text
04A1B2C3
04-A1-B2-C3
04:A1:B2:C3
```
remain distinct.
### Duplicate suppression
Hardware-level:
```text
Reader reports A, A, A, A
→ NFC adapter publishes A once
```
Application-level:
```text
Card A starts Playlist A
Card A detected again
→ Playlist A already active
→ no Spotify command
```
Both protections are intentional and independent.
### Card removal
Card removal does not stop playback.
Version 1 does not require `NfcCardRemoved`.
The adapter may track removal internally to re-arm detection.
### Required behavior
```text
NFC A detected        → playback A starts
NFC A removed         → playback continues
NFC A detected again  → no restart
NFC B detected        → playback B starts
NFC B removed         → playback continues
Unknown NFC detected  → playback continues
```
---
## 11. Configuration
Current adapter: `JSONConfigRepository`.
Behavior:
- loads JSON once;
- validates the full configuration;
- normalizes card IDs;
- converts entries into `PlaybackTarget`;
- stores targets in memory;
- performs no runtime writes;
- does not reload automatically.
Format:
```json
{
  "cards": {
    "04A1B2C3": {
      "uri": "spotify:playlist:123456",
      "name": "Kids Playlist"
    }
  }
}
```
Unknown cards return `None`.
Invalid configuration fails startup.
The controller never sees raw JSON.
---
## 12. Spotify Integration
Current adapter: `SpotifyWebApiPlayer`.
Responsibilities:
- start a playback context;
- target one Spotify Connect device;
- confirm requested playback;
- enforce finite timeouts;
- use remote state for play/pause;
- navigate tracks;
- read and update volume;
- clamp volume.
`play_context(target)` returns only when:
- `is_playing` is exactly `True`;
- the device ID matches;
- the context URI matches `target.uri`.
Otherwise it raises `TimeoutError` after bounded polling.
A concrete Spotify API client is still required for OAuth, token refresh, real Web API calls, and SDK response translation.
The intended playback device is a local Spotify Connect receiver on the Raspberry Pi, likely provided by `librespot`.
`librespot` process management remains outside application logic.
---
## 13. Lifecycle and Concurrency
The composition root constructs:
```text
EventBus
InputCoordinator
JSONConfigRepository
SpotifyPlayer implementation
FeedbackOutput implementation
PlayerController
NFC adapter
```
Startup:
```text
Linux boots
→ application starts
→ configuration validates
→ dependencies are constructed
→ handlers register
→ NFC adapter starts
→ application waits
```
Shutdown:
```text
shutdown signal
→ NFC adapter stops
→ worker thread exits
→ resources close
→ process exits
```
Version 1 uses:
- synchronous EventBus dispatch;
- one global non-blocking input lock;
- a background thread only for blocking NFC reads if required;
- synchronous Spotify commands;
- finite external-operation timeouts.
No application-wide `asyncio` architecture is required.
---
## 14. Error Handling
Startup failures such as missing config, malformed JSON, invalid mappings, or unavailable mandatory NFC hardware fail clearly.
Unknown card:
```text
no Spotify call
current playback continues
optional feedback
```
Spotify failure:
```text
exception or timeout propagates
InputCoordinator releases lock
previous active target remains unchanged
same card may be retried
```
Optional future hardware such as LEDs must not stop core NFC playback.
---
## 15. Read-only Runtime
The production Raspberry Pi should support a read-only operating system.
Runtime writes are not required for configuration, card mappings, playback state, or application state.
Benefits:
- reduced SD-card corruption risk;
- safe hard power-off;
- deterministic startup;
- recovery by reflashing.
Volatile or remote logging may be added without making the system partition writable.
---
## 16. Testing Strategy
Unit tests cover events, models, EventBus, InputCoordinator, PlayerController, configuration validation, and Spotify adapter behavior.
Adapter tests use deterministic fake clients or hardware boundaries.
Tests must not make real network calls, require Raspberry Pi hardware, or use real timeout sleeps.
Integration tests wire real application components with fake external ports.
Acceptance tests exercise:
```text
temporary JSON config
→ Application
→ InputCoordinator
→ EventBus
→ PlayerController
→ recording SpotifyPlayer
```
The PN532 adapter also requires Raspberry Pi hardware verification.
---
## 17. Current Status
Implemented:
- domain events and `PlaybackTarget`;
- synchronous `EventBus`;
- `InputCoordinator`;
- ports;
- `PlayerController`;
- current-target suppression;
- `JSONConfigRepository`;
- `SpotifyWebApiPlayer`;
- composition root;
- unit, integration, and acceptance tests.
Still required:
1. PN532 NFC adapter over SPI;
2. real Spotify API client and authentication;
3. minimal runtime feedback implementation;
4. production bootstrap and `main.py`;
5. Raspberry Pi deployment configuration;
6. local Spotify Connect playback engine;
7. device-level end-to-end verification.
---
## 18. MVP Completion Criteria
```text
Power on
→ Linux boots
→ Spotify Connect receiver is available
→ KidsSpotifyPlayer starts
→ PN532 waits for a card
→ known card detected
→ PlaybackTarget resolved
→ Spotify playback starts on the Pi
→ card removed
→ playback continues
→ same target ignored
→ different target starts
→ unknown target leaves playback unchanged
```
---
## 19. Accepted Decisions
1. Raspberry Pi Zero 2 W is the initial platform.
2. PN532 over SPI is the selected NFC hardware.
3. NFC is the primary MVP interface.
4. Events are immutable facts.
5. EventBus dispatch is synchronous.
6. Input is globally serialized.
7. Overlapping input is discarded, not queued.
8. Hardware duplicate suppression belongs in the NFC adapter.
9. Current-target suppression belongs in the PlayerController.
10. Card removal does not stop playback.
11. Unknown cards do not change playback.
12. Configuration is loaded once from read-only JSON.
13. Repositories return domain models.
14. Spotify state decisions belong in the Spotify adapter.
15. Playback start requires bounded confirmation.
16. Application state is in memory only.
17. Hardware and SDK details remain inside adapters.
18. Bootstrap owns lifecycle and dependency construction.
19. Runtime writes are not required for the MVP.
20. Buttons and visual feedback are not required for the first MVP.
---
## 20. Open Decisions
- exact PN532 Python library;
- PN532 polling interval and removal threshold;
- concrete Spotify SDK or HTTP client;
- OAuth token provisioning and refresh;
- `librespot` installation and service configuration;
- I²S DAC, amplifier, and speaker hardware;
- Raspberry Pi OS image;
- systemd service definitions;
- read-only root filesystem setup;
- production logging destination.
Decisions should be made only when needed for the next MVP step.