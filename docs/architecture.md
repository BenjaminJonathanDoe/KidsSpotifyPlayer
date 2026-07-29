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
- support a read-only operating system where runtime persistence is not required;
- serialize user input so only one command is handled at a time;
- discard additional user input while a command is still being processed.

The main architectural rule is:

> Application logic must not know whether an input originated from Raspberry Pi GPIO, an ESP32, a fake test adapter, or another future source.

---

## 3. System context

```text
NFC Reader ─┐
Buttons ────┼──> Input Adapters ───> Input Coordinator ───> Event Bus
ESP32* ─────┘                               │                    │
                                           │                    ▼
                                           │            Player Controller
                                           │                    │
                                           │                    ├──> Spotify Player
                                           │                    ├──> Audio / Volume
                                           │                    ├──> Feedback / LEDs
                                           │                    └──> State Management
                                           │
                                           └──> Global non-blocking input lock

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

The application and `PlayerController` never poll hardware. They receive neutral events from input adapters through the `InputCoordinator` and synchronous `EventBus`.

### 4.3 Ports

Ports describe what the application needs from external systems.

There are two categories of ports.

#### Event-source ports

Event-source ports represent input components that produce domain events.

Examples:

- `EventSource`;
- `ButtonInput`;
- `NfcReader`;
- future `Esp32Input`.

They expose lifecycle operations only:

```python
class EventSource:
    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...
```

Concrete implementations receive their event-publishing dependency during construction.

#### Action and service ports

Action and service ports are called by the application to perform work or retrieve data.

Examples:

- `SpotifyPlayer`;
- `FeedbackOutput`;
- `AudioOutput`;
- `ConfigRepository`.

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

A port describes capability, not implementation.

### 4.4 Adapters

Adapters implement ports for concrete technologies.

Initial adapter groups:

- Raspberry Pi GPIO and hardware adapters;
- Spotify adapter;
- configuration file adapter;
- fake adapters for Windows development and automated tests.

Input adapters are push-based event sources. Concrete button and NFC adapters receive an `InputCoordinator` during construction and use it to publish neutral domain events while running.

Examples include publishing:

- `PlayPausePressed`;
- `NextTrackPressed`;
- `PreviousTrackPressed`;
- `VolumeUpPressed`;
- `VolumeDownPressed`;
- `NfcCardDetected`;
- `NfcCardRemoved`.

Duplicate NFC suppression belongs in the NFC adapter.

Button debouncing belongs in the button adapter.

Future adapter groups may include:

- ESP32 remote input;
- web or mobile control;
- alternative NFC hardware;
- alternative feedback hardware.

### 4.5 Input and event flow

Input adapters are lifecycle-controlled event sources:

- buttons;
- NFC;
- future ESP32 or remote inputs.

They start monitoring when `start()` is called and stop monitoring when `stop()` is called.

They may use callbacks, interrupts, polling loops, or background threads internally, but these implementation details remain inside the adapter.

The application never polls hardware directly.

The `InputCoordinator` is the single entry point for user-generated domain events.

### 4.6 Infrastructure

Infrastructure wires the application together and handles startup, shutdown, logging, process lifecycle, dependency construction, and lifecycle ownership.

The composition root belongs in `main.py` or a dedicated bootstrap module.

Bootstrap is responsible for:

1. creating the `EventBus`;
2. creating the `InputCoordinator`;
3. creating the `PlayerController`;
4. subscribing controller handlers;
5. creating event-source adapters;
6. starting event sources;
7. stopping event sources during shutdown.

The `PlayerController` does not start or stop hardware adapters.

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
    ├── input/
    │   └── coordinator.py
    │
    ├── ports/
    │   ├── event_source.py
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
├── input/
├── ports/
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

## 9. Global input serialization

All user input sources share a single `InputCoordinator`.

Before publishing a domain input event, an adapter passes the event to the coordinator.

The coordinator atomically attempts to acquire a non-blocking global lock.

If the lock cannot be acquired:

- the input is discarded;
- the input is not queued;
- the input is not replayed later;
- no event is published.

If the lock is acquired:

1. the coordinator publishes the event through the synchronous `EventBus`;
2. all registered handlers execute synchronously;
3. the lock remains held until all handlers have completed;
4. the lock is released in a `finally` block.

Conceptual implementation:

```python
class InputCoordinator:
    def publish(self, event: Event) -> bool:
        if not self._lock.acquire(blocking=False):
            return False

        try:
            self._event_bus.publish(event)
            return True
        finally:
            self._lock.release()
```

This design guarantees:

- only one user input command is processed at a time;
- all additional button and NFC input is ignored during command execution;
- no command backlog develops;
- the `PlayerController` is not invoked concurrently by user input;
- a failure or exception does not permanently lock input.

Existing audio playback normally continues while a command is being processed because playback is handled by the Spotify or audio backend rather than by the input thread.

External operations must use finite timeouts so that an unavailable Spotify service cannot keep input disabled indefinitely.

### 9.1 Command completion boundary

The input lock remains active until the command has reached a defined completion state.

For NFC playback requests, completion means one of:

- playback has been confirmed as started;
- playback startup has failed;
- the operation has timed out.

For button commands, completion means one of:

- the requested action has completed successfully;
- the action has failed;
- the operation has timed out.

A Spotify adapter must therefore not return immediately after merely sending a command if playback confirmation is required by the use case.

---

## 10. Core use cases

### 10.1 Known NFC card

```text
NFC reader detects card
→ NFC adapter suppresses duplicates
→ InputCoordinator tries to acquire input lock
→ lock acquired
→ NfcCardDetected(card_id) published
→ PlayerController looks up the card
→ mapping found
→ SpotifyPlayer.play_context(uri)
→ wait for playback confirmation, failure, or timeout
→ PlaybackStarted or PlaybackFailed
→ feedback updated
→ EventBus handling completes
→ input lock released
```

While the lock is held:

- additional NFC cards are ignored;
- button presses are ignored;
- existing audio playback continues until the new playback starts.

### 10.2 Unknown NFC card

```text
NFC reader detects card
→ InputCoordinator acquires input lock
→ NfcCardDetected(card_id)
→ no mapping found
→ no Spotify command
→ warning is logged
→ short error feedback
→ existing playback and state remain unchanged
→ input lock released
```

An unknown card must not stop currently playing content.

### 10.3 Card remains on reader

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

### 10.4 Play/Pause

```text
PlayPausePressed
→ InputCoordinator acquires input lock
→ if state is PLAYING: pause
→ if state is PAUSED: resume
→ if no content has been selected: no playback action
→ wait for success, failure, or timeout
→ input lock released
```

Pressing Play/Pause before content has been selected must not start random or previously remembered content.

### 10.5 Next track

```text
NextTrackPressed
→ InputCoordinator acquires input lock
→ SpotifyPlayer.next_track()
→ wait for success, failure, or timeout
→ optional TrackChanged event
→ short confirmation feedback
→ input lock released
```

If no playback is active, the command may be ignored and logged.

### 10.6 Previous track

```text
PreviousTrackPressed
→ InputCoordinator acquires input lock
→ SpotifyPlayer.previous_track()
→ wait for success, failure, or timeout
→ optional TrackChanged event
→ short confirmation feedback
→ input lock released
```

The exact restart-versus-previous behavior is delegated to the Spotify backend.

### 10.7 Volume increase

```text
VolumeUpPressed
→ InputCoordinator acquires input lock
→ current volume + configured step
→ clamp to configured maximum
→ SpotifyPlayer or AudioOutput sets volume
→ VolumeChanged
→ input lock released
```

Recommended defaults:

```text
step: 5 %
maximum: 70 %
```

### 10.8 Volume decrease

```text
VolumeDownPressed
→ InputCoordinator acquires input lock
→ current volume - configured step
→ clamp to configured minimum
→ SpotifyPlayer or AudioOutput sets volume
→ VolumeChanged
→ input lock released
```

Recommended minimum:

```text
minimum: 0 %
```

A volume of 0 % means muted, not paused.

### 10.9 Spotify unavailable

```text
input event occurs
→ InputCoordinator acquires input lock
→ controller requests Spotify action
→ Spotify command fails or times out
→ PlaybackFailed or SpotifyUnavailable
→ state becomes OFFLINE
→ error feedback
→ application keeps running
→ input lock released
→ connection may be retried later
```

### 10.10 Hardware failure

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

## 11. Event bus

Version 1 uses a simple synchronous event bus.

Responsibilities:

- register subscribers by event type;
- publish events to subscribers;
- isolate publishers from subscribers;
- preserve deterministic subscriber order;
- avoid silently losing errors.

The event bus should not contain domain decisions.

Blocking hardware readers may run in background threads and submit events through the `InputCoordinator`.

The initial architecture deliberately avoids making the whole application asynchronous. `asyncio` may be introduced later if real requirements justify it.

The event bus invokes subscribers in the same thread that publishes the event.

For user input events, the `InputCoordinator` ensures that only one such dispatch is active at a time.

---

## 12. Concurrency

Recommended initial model:

- main process owns application lifecycle;
- synchronous event dispatch;
- global non-blocking input lock in the `InputCoordinator`;
- dedicated background thread for blocking NFC reads if necessary;
- GPIO callbacks or a small input thread for buttons;
- Spotify calls remain synchronous initially;
- external operations use finite timeouts;
- clean stop signals for all worker threads.

Shared mutable state should be minimized.

State changes should be centralized through the application controller.

User-input handlers must not execute concurrently.

System or lifecycle events that do not originate from the `InputCoordinator` may require separate concurrency review when introduced.

---

## 13. Configuration

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

## 14. Feedback and LEDs

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
| Input locked / command running | Optional busy indication |
| NFC accepted | Short confirmation |
| Unknown NFC card | Short error signal |
| Volume changed | Very short confirmation |

Colors remain hardware-dependent and will be decided when the LED hardware is selected.

---

## 15. Hardware abstraction

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

Input serialization does not belong in individual adapters. It belongs in the shared `InputCoordinator`.

---

## 16. Spotify integration boundary

The `SpotifyPlayer` port should expose application-oriented operations rather than raw API calls.

Required capabilities:

- start playback of a Spotify context URI;
- pause;
- resume;
- skip forward;
- skip backward;
- set or retrieve volume where supported;
- report availability;
- confirm completion where required by the use case;
- translate backend failures into defined application errors or events;
- apply finite timeouts to blocking operations.

The adapter may later use Spotify Connect, a local playback service, or another mechanism without changing the controller.

For NFC-triggered playback, `play_context()` or an equivalent application-oriented operation must not signal completion until playback has started, failed, or timed out.

The exact Spotify playback implementation remains a separate technical decision.

---

## 17. Windows development and fake adapters

Development must be possible without Raspberry Pi hardware.

Fake adapters should support:

- manually simulating NFC cards;
- manually simulating button presses;
- recording Spotify commands;
- simulating delayed command completion;
- simulating failures and timeouts;
- simulating input discarded while the coordinator is locked;
- collecting requested feedback;
- deterministic automated tests.

Example:

```text
FakeNfcReader.emit_card("04A1B2C3")
→ InputCoordinator
→ NfcCardDetected
→ same application flow as the Raspberry Pi adapter
```

The application controller and domain logic should run unchanged on Windows and Raspberry Pi.

---

## 18. Future ESP32 extension

A future ESP32 may read buttons or NFC and send neutral input messages to the Raspberry Pi.

Possible transport options include Wi-Fi, Bluetooth, serial, or another suitable protocol. The transport is not selected in version 1.

Example remote message:

```json
{
  "event": "VolumeUpPressed"
}
```

An ESP32 adapter on the Raspberry Pi translates the message into the same internal event used by local GPIO and submits it through the same `InputCoordinator`.

No application or controller redesign should be required.

Inputs from the ESP32 are subject to the same global input lock as local NFC and button inputs.

---

## 19. Error handling principles

- Temporary network or Spotify failures must not terminate the application.
- Recoverable failures should be logged and retried where sensible.
- Unknown NFC cards are normal user input, not fatal errors.
- A non-essential LED failure must not stop playback.
- Invalid startup configuration may prevent transition to `READY`.
- Errors exposed to the controller should use defined types rather than backend-specific exceptions.
- Logs should include enough context for diagnosis without exposing credentials.
- The `InputCoordinator` must release its lock after success, failure, timeout, or exception.
- External operations must use finite timeouts.
- Inputs received while the coordinator is locked are intentionally discarded.

---

## 20. Logging

Logging should cover:

- application startup and shutdown;
- configuration loading;
- detected NFC card IDs;
- resolved playback targets;
- button events;
- discarded input while locked;
- input lock acquisition and release where useful;
- playback commands;
- command timeouts;
- state changes;
- hardware availability;
- network and Spotify availability;
- retry attempts;
- failures and stack traces where useful.

Sensitive data such as Spotify credentials, tokens, and secrets must never be logged.

Log persistence is optional. A read-only system may use console or volatile logs unless a separate writable or remote logging strategy is introduced.

---

## 21. Testing strategy

### Unit tests

Unit tests should cover:

- NFC card resolution;
- unknown-card behavior;
- Play/Pause state rules;
- volume clamping;
- state transitions;
- recoverable and fatal failures;
- event bus dispatch;
- input coordinator locking;
- input discard while busy;
- lock release after successful handling;
- lock release after exceptions;
- lock release after timeouts;
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
- real input coordinator;
- fake input adapters;
- fake Spotify and feedback adapters.

This provides confidence in complete use-case flows without requiring physical hardware.

Integration tests should verify that:

- a second input is discarded while a command is running;
- no queued input is replayed afterward;
- existing playback state is preserved until a new command completes;
- input becomes available again after success, failure, or timeout.

---

## 22. Version 1 scope

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
- global input serialization;
- discarded input while commands are running;
- finite command timeouts;
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
- queued input commands;
- replay of ignored input;
- complex playback queues;
- voice control;
- dynamic Spotify search.

---

## 23. Architecture decisions

The initial architecture establishes these decisions:

1. A central `PlayerController` owns application decisions.
2. Hardware produces neutral events.
3. The controller accesses external systems only through ports.
4. Raspberry Pi-specific code exists only in adapters.
5. Fake adapters are provided for Windows development and tests.
6. The event bus is synchronous in version 1.
7. Input adapters are push-based lifecycle-controlled event sources.
8. Blocking hardware readers may use dedicated background threads.
9. All user input passes through one shared `InputCoordinator`.
10. The coordinator uses an atomic non-blocking lock.
11. Only one user input command is processed at a time.
12. Additional input while a command is running is discarded.
13. Ignored input is not queued or replayed.
14. Existing audio playback normally continues during command handling.
15. Input remains locked until the command succeeds, fails, or times out.
16. External operations use finite timeouts.
17. Application state is stored only in memory.
18. Configuration is loaded from a file during startup.
19. Unknown NFC cards do not change current playback.
20. Volume is limited by configurable minimum and maximum values.
21. Network or Spotify outages do not terminate the application.
22. Runtime writes to the SD card are not required for version 1.
23. An ESP32 can later be added as an input adapter without redesigning the controller.
24. A separate command bus is not required initially.
25. Bootstrap owns event-source lifecycle.
26. The `PlayerController` never polls or starts hardware.

---

## 24. Open technical decisions

The following questions remain intentionally open:

- exact NFC reader model and communication protocol;
- exact Spotify playback mechanism;
- exact method for confirming playback start;
- timeout values for Spotify commands;
- whether volume is controlled through Spotify, the local audio stack, or both;
- exact LED hardware and color mapping;
- whether a busy LED indication is required;
- configuration format, such as YAML, TOML, or JSON;
- retry timing and backoff strategy;
- exact thread model for the selected NFC library;
- target Raspberry Pi operating system and service manager setup;
- future ESP32 communication transport.

These decisions should be made when the relevant hardware or implementation work begins.

---

## 25. Initial implementation order

Recommended sequence:

1. domain models and event definitions;
2. player state;
3. synchronous event bus;
4. port interfaces;
5. input coordinator;
6. fake adapters;
7. PlayerController;
8. unit and integration tests;
9. configuration loader and validation;
10. logging and application bootstrap;
11. Raspberry Pi button adapter;
12. Raspberry Pi NFC adapter;
13. feedback/LED adapter;
14. Spotify adapter;
15. audio integration;
16. target-device integration and system service setup.
