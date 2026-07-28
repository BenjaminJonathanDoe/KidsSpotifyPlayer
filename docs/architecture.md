# KidsSpotifyPlayer Architecture

## 1. Purpose

KidsSpotifyPlayer is a child-friendly Spotify player running on a Raspberry Pi Zero 2 W. It is controlled through NFC cards and physical buttons and provides simple visual feedback through LEDs.

The first implementation connects NFC, buttons, LEDs, Spotify playback, and audio directly to the Raspberry Pi. The software must remain modular so that an ESP32 can later be added as a remote input controller without redesigning the application.

---

## 2. Architectural goals

The architecture should:

- keep hardware-specific code separate from application logic;
- allow development and testing on Windows without Raspberry Pi hardware;
- use neutral events for user and system actions;
- make hardware implementations replaceable;
- support a future ESP32 input controller;
- remain understandable and lightweight enough for a Raspberry Pi Zero 2 W;
- continue operating through temporary network or Spotify outages;
- support a read-only operating system where runtime persistence is not required.

The main architectural rule is:

> Application logic must not know whether an input originated from Raspberry Pi GPIO, an ESP32, a fake test adapter, or another future source.

---

## 3. System context

```text
NFC Reader ─┐
Buttons ────┼──> Input Adapters ───> Event Bus ───> Player Controller
ESP32* ─────┘                              │
                                          ├──> Spotify Player
                                          ├──> Audio / Volume
                                          ├──> Feedback / LEDs
                                          └──> State Management

* Future extension, not part of version 1.
```

The Raspberry Pi Zero 2 W initially performs all core functions:

- reads NFC cards;
- reads physical buttons;
- controls LEDs;
- controls Spotify playback;
- outputs audio through I²S;
- runs the application and its state management.

---

## 4. Architectural layers

### 4.1 Domain

The domain contains neutral concepts that do not depend on Raspberry Pi libraries, GPIO pins, Spotify SDKs, or configuration file formats.

Examples:

- events;
- player states;
- playback targets;
- configuration models;
- error types.

The domain must be importable and testable on any supported platform.

### 4.2 Application

The application layer contains the use-case logic.

Its central component is the `PlayerController`. It receives events, applies rules, invokes ports, and updates the current state.

Examples of decisions made here:

- resolving an NFC card to a Spotify URI;
- deciding whether Play/Pause should pause or resume;
- applying volume limits;
- handling an unknown NFC card;
- reacting to recoverable and non-recoverable failures.

The application layer must not access GPIO, SPI, I²C, I²S, network APIs, YAML, or JSON directly.

### 4.3 Ports

Ports describe what the application needs from external systems.

Examples:

- `SpotifyPlayer`;
- `NfcReader`;
- `ButtonInput`;
- `FeedbackOutput`;
- `ConfigRepository`;
- `AudioOutput`.

A port describes capability, not implementation.

Example:

```python
class SpotifyPlayer:
    def play_context(self, uri: str) -> None:
        ...

    def pause(self) -> None:
        ...

    def resume(self) -> None:
        ...

    def next_track(self) -> None:
        ...

    def previous_track(self) -> None:
        ...

    def set_volume(self, volume_percent: int) -> None:
        ...
```

### 4.4 Adapters

Adapters implement ports for concrete technologies.

Initial adapter groups:

- Raspberry Pi GPIO and hardware adapters;
- Spotify adapter;
- configuration file adapter;
- fake adapters for Windows development and automated tests.

Future adapter groups may include:

- ESP32 remote input;
- web or mobile control;
- alternative NFC hardware;
- alternative feedback hardware.

### 4.5 Infrastructure

Infrastructure wires the application together and handles startup, shutdown, logging, process lifecycle, and dependency construction.

The composition root belongs in `main.py` or a dedicated bootstrap module.

---

## 5. Proposed package structure

```text
src/
└── kidsspotifyplayer/
    ├── application/
    │   ├── controller.py
    │   ├── state.py
    │   └── use_cases.py
    │
    ├── domain/
    │   ├── events.py
    │   ├── commands.py
    │   ├── models.py
    │   └── errors.py
    │
    ├── event_bus/
    │   └── bus.py
    │
    ├── ports/
    │   ├── nfc_reader.py
    │   ├── button_input.py
    │   ├── feedback_output.py
    │   ├── spotify_player.py
    │   ├── audio_output.py
    │   └── config_repository.py
    │
    ├── adapters/
    │   ├── raspberry_pi/
    │   │   ├── gpio_buttons.py
    │   │   ├── nfc_reader.py
    │   │   ├── leds.py
    │   │   └── audio.py
    │   │
    │   ├── spotify/
    │   │   └── spotify_adapter.py
    │   │
    │   ├── config/
    │   │   └── file_config_repository.py
    │   │
    │   └── fake/
    │       ├── fake_buttons.py
    │       ├── fake_nfc.py
    │       ├── fake_feedback.py
    │       └── fake_spotify.py
    │
    ├── config/
    │   ├── loader.py
    │   └── models.py
    │
    ├── bootstrap.py
    └── main.py
```

Tests should mirror the source structure where practical:

```text
tests/
├── application/
├── domain/
├── event_bus/
├── adapters/
└── integration/
```

---

## 6. Event model

Events state that something has happened. They should be immutable data objects where practical.

### 6.1 Input events

#### `NfcCardDetected`

Data:

```text
card_id: str
```

Meaning:

An NFC card has been detected for the first time after being absent.

#### `NfcCardRemoved`

Data:

```text
card_id: str
```

Meaning:

The currently detected card has been removed.

This event is useful for preventing repeated triggering while a card remains on the reader.

#### `PlayPausePressed`

No data.

#### `NextTrackPressed`

No data.

#### `PreviousTrackPressed`

No data.

#### `VolumeUpPressed`

No data.

#### `VolumeDownPressed`

No data.

#### `ShutdownRequested`

No data.

This event is reserved for a future controlled restart, shutdown, or maintenance action. It is not required for ordinary daily power-off because a physical kill switch may be used.

### 6.2 Application lifecycle events

#### `ApplicationStarted`

The process has started and initialization begins.

#### `ApplicationReady`

Configuration and required components are initialized and the player can accept input.

#### `ApplicationStopping`

Controlled shutdown or restart is in progress.

### 6.3 Playback events

#### `PlaybackStarted`

Possible data:

```text
context_uri: str | None
track_name: str | None
```

#### `PlaybackPaused`

No required data.

#### `TrackChanged`

Possible data:

```text
track_name: str | None
artist_name: str | None
```

#### `VolumeChanged`

Data:

```text
volume_percent: int
```

#### `PlaybackFailed`

Data:

```text
reason: str
recoverable: bool
```

### 6.4 Connectivity and availability events

#### `NetworkAvailable`

The required network connection is available.

#### `NetworkUnavailable`

The network is unavailable.

#### `SpotifyAvailable`

The Spotify service can accept commands.

#### `SpotifyUnavailable`

The Spotify service or playback target is unavailable.

### 6.5 Failure events

#### `ConfigurationFailed`

Data:

```text
reason: str
```

Examples:

- invalid configuration syntax;
- missing required values;
- duplicate card assignment;
- invalid volume limits.

#### `HardwareFailed`

Data:

```text
component: str
reason: str
recoverable: bool
```

Examples:

- NFC reader unavailable;
- GPIO initialization failed;
- LED output unavailable;
- audio output unavailable.

---

## 7. Commands

Events say that something happened. Commands express an intended action.

The first implementation does not require a separate command bus. Commands may be represented through direct port method calls.

Conceptual commands:

- `PlayContext`;
- `PausePlayback`;
- `ResumePlayback`;
- `SkipNext`;
- `SkipPrevious`;
- `SetVolume`;
- `ShowFeedback`;
- `RetrySpotifyConnection`.

Example flow:

```text
NfcCardDetected
→ PlayerController resolves the card
→ SpotifyPlayer.play_context(uri)
→ PlaybackStarted
```

---

## 8. Player state

The application keeps a central in-memory state.

```text
STARTING
READY
PLAYING
PAUSED
OFFLINE
ERROR
STOPPING
```

### `STARTING`

Configuration and hardware are being initialized.

### `READY`

The system is operational but no playback is active.

### `PLAYING`

Playback is active.

### `PAUSED`

Playback is paused.

### `OFFLINE`

The application is running but network or Spotify is unavailable.

### `ERROR`

A serious failure prevents normal operation.

### `STOPPING`

The application is shutting down or restarting in a controlled manner.

The state does not need to be written to the SD card in version 1.

---

## 9. Core use cases

### 9.1 Known NFC card

```text
NFC reader detects card
→ NfcCardDetected(card_id)
→ PlayerController looks up the card
→ mapping found
→ SpotifyPlayer.play_context(uri)
→ PlaybackStarted
→ state becomes PLAYING
→ feedback indicates playback
```

### 9.2 Unknown NFC card

```text
NFC reader detects card
→ NfcCardDetected(card_id)
→ no mapping found
→ no Spotify command
→ warning is logged
→ short error feedback
→ existing playback and state remain unchanged
```

An unknown card must not stop currently playing content.

### 9.3 Card remains on reader

```text
card detected
→ one NfcCardDetected event

card remains present
→ no repeated event

card removed
→ NfcCardRemoved

card presented again
→ a new NfcCardDetected event
```

Duplicate suppression belongs in the NFC adapter.

### 9.4 Play/Pause

```text
PlayPausePressed
→ if state is PLAYING: pause
→ if state is PAUSED: resume
→ if no content has been selected: no playback action
```

Pressing Play/Pause before content has been selected must not start random or previously remembered content.

### 9.5 Next track

```text
NextTrackPressed
→ SpotifyPlayer.next_track()
→ optional TrackChanged event
→ short confirmation feedback
```

If no playback is active, the command may be ignored and logged.

### 9.6 Previous track

```text
PreviousTrackPressed
→ SpotifyPlayer.previous_track()
→ optional TrackChanged event
→ short confirmation feedback
```

The exact restart-versus-previous behavior is delegated to the Spotify backend.

### 9.7 Volume increase

```text
VolumeUpPressed
→ current volume + configured step
→ clamp to configured maximum
→ SpotifyPlayer or AudioOutput sets volume
→ VolumeChanged
```

Recommended defaults:

```text
step: 5 %
maximum: 70 %
```

### 9.8 Volume decrease

```text
VolumeDownPressed
→ current volume - configured step
→ clamp to configured minimum
→ SpotifyPlayer or AudioOutput sets volume
→ VolumeChanged
```

Recommended minimum:

```text
minimum: 0 %
```

A volume of 0 % means muted, not paused.

### 9.9 Spotify unavailable

```text
input event occurs
→ controller requests Spotify action
→ Spotify command fails
→ PlaybackFailed or SpotifyUnavailable
→ state becomes OFFLINE
→ error feedback
→ application keeps running
→ connection is retried later
```

### 9.10 Hardware failure

Recoverable example:

```text
LED output fails
→ HardwareFailed(recoverable=True)
→ warning is logged
→ player continues without visual feedback
```

Serious example:

```text
NFC reader fails and no alternate input exists
→ HardwareFailed
→ state may become ERROR
→ application remains diagnosable
```

---

## 10. Event bus

Version 1 uses a simple synchronous event bus.

Responsibilities:

- register subscribers by event type;
- publish events to subscribers;
- isolate publishers from subscribers;
- log subscriber failures;
- avoid silently losing errors.

The event bus should not contain domain decisions.

Blocking hardware readers may run in background threads and publish events into the bus.

The initial architecture deliberately avoids making the whole application asynchronous. `asyncio` may be introduced later if real requirements justify it.

---

## 11. Concurrency

Recommended initial model:

- main process owns application lifecycle;
- synchronous event dispatch;
- dedicated background thread for blocking NFC reads if necessary;
- GPIO callbacks or a small input thread for buttons;
- Spotify calls remain synchronous initially unless latency causes input problems;
- clean stop signals for all worker threads.

Shared mutable state should be minimized. State changes should be centralized through the application controller.

---

## 12. Configuration

Configuration is loaded at startup from a read-only file.

Example:

```yaml
cards:
  "04A1B2C3":
    name: "Kinderlieder"
    spotify_uri: "spotify:playlist:123456"

  "04D4E5F6":
    name: "Hörspiele"
    spotify_uri: "spotify:album:987654"

volume:
  default: 35
  step: 5
  minimum: 0
  maximum: 70
```

The controller must not parse YAML or JSON itself. A configuration adapter loads and validates the file and returns domain models.

Version 1 does not require runtime configuration changes. Adding NFC cards or changing credentials may be handled by updating and reflashing the image.

Secrets must not be committed to Git.

---

## 13. Feedback and LEDs

The controller requests semantic feedback and does not set GPIO pins directly.

Examples:

```text
show_state(PLAYING)
show_state(PAUSED)
show_card_accepted()
show_unknown_card()
show_volume_changed()
show_error()
```

Suggested initial patterns:

| State or action | Feedback |
|---|---|
| `STARTING` | Slow blink |
| `READY` | Constant light |
| `PLAYING` | Constant light or gentle pulse |
| `PAUSED` | Short periodic blink |
| `OFFLINE` | Slow double blink |
| `ERROR` | Fast blink |
| NFC accepted | Short confirmation |
| Unknown NFC card | Short error signal |
| Volume changed | Very short confirmation |

Colors remain hardware-dependent and will be decided when the LED hardware is selected.

---

## 14. Hardware abstraction

Hardware-specific dependencies must be confined to adapters.

Examples of details that must not leak into the application layer:

- GPIO pin numbers;
- pull-up or pull-down configuration;
- switch debouncing;
- SPI bus numbers;
- NFC reader register access;
- I²S device names;
- Raspberry Pi library types.

Button debouncing belongs in the GPIO adapter.

NFC duplicate suppression belongs in the NFC adapter.

---

## 15. Spotify integration boundary

The `SpotifyPlayer` port should expose application-oriented operations rather than raw API calls.

Required capabilities:

- start playback of a Spotify context URI;
- pause;
- resume;
- skip forward;
- skip backward;
- set or retrieve volume where supported;
- report availability;
- translate backend failures into defined application errors or events.

The adapter may later use Spotify Connect, a local playback service, or another mechanism without changing the controller.

The exact Spotify playback implementation remains a separate technical decision.

---

## 16. Windows development and fake adapters

Development must be possible without Raspberry Pi hardware.

Fake adapters should support:

- manually simulating NFC cards;
- manually simulating button presses;
- recording Spotify commands;
- simulating failures and offline states;
- collecting requested feedback;
- deterministic automated tests.

Example:

```text
FakeNfcReader.emit_card("04A1B2C3")
→ same NfcCardDetected event as the Raspberry Pi adapter
```

The application controller and domain logic should run unchanged on Windows and Raspberry Pi.

---

## 17. Future ESP32 extension

A future ESP32 may read buttons or NFC and send neutral input messages to the Raspberry Pi.

Possible transport options include Wi-Fi, Bluetooth, serial, or another suitable protocol. The transport is not selected in version 1.

Example remote message:

```json
{
  "event": "VolumeUpPressed"
}
```

An ESP32 adapter on the Raspberry Pi translates the message into the same internal event used by local GPIO.

No application or controller redesign should be required.

---

## 18. Error handling principles

- Temporary network or Spotify failures must not terminate the application.
- Recoverable failures should be logged and retried where sensible.
- Unknown NFC cards are normal user input, not fatal errors.
- A non-essential LED failure must not stop playback.
- Invalid startup configuration may prevent transition to `READY`.
- Errors exposed to the controller should use defined types rather than backend-specific exceptions.
- Logs should include enough context for diagnosis without exposing credentials.

---

## 19. Logging

Logging should cover:

- application startup and shutdown;
- configuration loading;
- detected NFC card IDs;
- resolved playback targets;
- button events;
- playback commands;
- state changes;
- hardware availability;
- network and Spotify availability;
- retry attempts;
- failures and stack traces where useful.

Sensitive data such as Spotify credentials, tokens, and secrets must never be logged.

Log persistence is optional. A read-only system may use console or volatile logs unless a separate writable or remote logging strategy is introduced.

---

## 20. Testing strategy

### Unit tests

Unit tests should cover:

- NFC card resolution;
- unknown-card behavior;
- Play/Pause state rules;
- volume clamping;
- state transitions;
- recoverable and fatal failures;
- event bus dispatch;
- controller behavior with fake ports.

### Adapter tests

Where possible, adapters should be tested independently from the controller.

Raspberry Pi hardware adapters may need:

- tests with mocked hardware libraries;
- integration tests executed on the target device;
- manual hardware verification.

### Integration tests

Integration tests should wire:

- real controller;
- real event bus;
- fake input adapters;
- fake Spotify and feedback adapters.

This provides confidence in complete use-case flows without requiring physical hardware.

---

## 21. Version 1 scope

### Included

- NFC card detection;
- mapping NFC IDs to Spotify URIs;
- playback start;
- Play/Pause;
- next and previous track;
- volume up and down;
- configurable volume limits;
- LED or equivalent status feedback;
- controlled error handling;
- logging;
- fake adapters for Windows;
- Raspberry Pi adapters for real hardware;
- in-memory state;
- startup configuration from file.

### Not included initially

- display;
- user profiles;
- web interface;
- configuration editing on the device;
- persistent playback state;
- battery-level display;
- automatic power-off;
- ESP32 communication;
- complex playback queues;
- voice control;
- dynamic Spotify search.

---

## 22. Architecture decisions

The initial architecture establishes these decisions:

1. A central `PlayerController` owns application decisions.
2. Hardware produces neutral events.
3. The controller accesses external systems only through ports.
4. Raspberry Pi-specific code exists only in adapters.
5. Fake adapters are provided for Windows development and tests.
6. The event bus is synchronous in version 1.
7. Blocking hardware readers may use dedicated background threads.
8. Application state is stored only in memory.
9. Configuration is loaded from a file during startup.
10. Unknown NFC cards do not change current playback.
11. Volume is limited by configurable minimum and maximum values.
12. Network or Spotify outages do not terminate the application.
13. Runtime writes to the SD card are not required for version 1.
14. An ESP32 can later be added as an input adapter without redesigning the controller.
15. A separate command bus is not required initially.

---

## 23. Open technical decisions

The following questions remain intentionally open:

- exact NFC reader model and communication protocol;
- exact Spotify playback mechanism;
- whether volume is controlled through Spotify, the local audio stack, or both;
- exact LED hardware and color mapping;
- configuration format, such as YAML, TOML, or JSON;
- retry timing and backoff strategy;
- exact thread model for the selected NFC library;
- target Raspberry Pi operating system and service manager setup;
- future ESP32 communication transport.

These decisions should be made when the relevant hardware or implementation work begins.

---

## 24. Initial implementation order

Recommended sequence:

1. domain models and event definitions;
2. player state;
3. synchronous event bus;
4. port interfaces;
5. fake adapters;
6. `PlayerController`;
7. unit and integration tests;
8. configuration loader and validation;
9. logging and application bootstrap;
10. Raspberry Pi button adapter;
11. Raspberry Pi NFC adapter;
12. feedback/LED adapter;
13. Spotify adapter;
14. audio integration;
15. target-device integration and system service setup.
