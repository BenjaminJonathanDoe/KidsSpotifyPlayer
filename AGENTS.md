# KidsSpotifyPlayer - Engineering Guide

> Architecture: see `docs/architecture.md`
>
> This document describes how contributors (human or AI) should work in this repository.

---

# 1. Project Goal

KidsSpotifyPlayer is a Raspberry Pi Zero 2 W based Spotify player for children.

The MVP interaction is intentionally simple:

```text
NFC card detected
→ resolve playback target
→ start Spotify playback
→ playback continues after card removal
```

The architecture is deliberately modular so additional hardware (buttons, LEDs, ESP32, displays, etc.) can be added without changing the application layer.

---

# 2. Current MVP Scope

Implemented:

- Domain models
- Domain events
- EventBus
- InputCoordinator
- PlayerController
- JSONConfigRepository
- SpotifyWebApiPlayer
- Composition root
- Unit tests
- Integration tests
- Acceptance tests

Still required:

- PN532 NFC adapter over SPI
- Spotify API runtime client
- bootstrap.py
- main.py
- Raspberry Pi deployment
- End-to-end hardware test

Not part of MVP:

- Buttons
- LEDs
- Display
- Battery management
- ESP32 communication

---

# 3. Repository Structure

```
src/
    domain/
    application/
    ports/
    adapters/
    event_bus/
    input/

tests/
    domain/
    application/
    adapters/
    acceptance/
```

Tests mirror the production structure.

---

# 4. Architecture Rules

Always follow `docs/architecture.md`.

Important rules:

- Domain never depends on infrastructure.
- Application never imports adapters.
- Ports define capabilities only.
- Adapters implement ports.
- Infrastructure wires dependencies.

Responsibilities:

PlayerController

- application decisions
- playback selection
- current target suppression

JSONConfigRepository

- JSON parsing
- configuration validation
- PlaybackTarget creation

SpotifyWebApiPlayer

- Spotify state interpretation
- playback confirmation
- volume handling

PN532 adapter

- NFC hardware
- duplicate hardware read suppression
- UID normalization

Never move responsibilities between layers without explicit approval.

---

# 5. Development Workflow

For every change:

1. Read existing code.
2. Understand surrounding tests.
3. Decide which layer owns the change.
4. Explain your reasoning briefly.
5. Write failing tests first whenever practical.
6. Implement the smallest possible change.
7. Run targeted tests.
8. Run the full test suite.
9. Review the diff.
10. Stop.

Never commit automatically.

Never merge automatically.

Wait for user review.

---

# 6. Testing Rules

Tests must be:

- deterministic
- isolated
- repeatable
- hardware independent

Prefer:

- fake clients
- injected clocks
- injected dependencies

Avoid:

- real sleep()
- real network requests
- Raspberry Pi hardware
- Spotify servers

Acceptance tests should exercise public interfaces instead of implementation details.

---

# 7. Coding Standards

Prefer:

- constructor injection
- composition
- immutable models
- explicit dependencies
- small classes
- descriptive names

Avoid:

- globals
- singletons
- service locators
- dependency injection frameworks
- speculative abstractions

Fail fast whenever configuration is invalid.

---

# 8. Current Roadmap

Priority order:

1. PN532 NFC adapter
2. Spotify runtime client
3. bootstrap.py
4. main.py
5. Raspberry Pi integration
6. Hardware validation

Only work on one roadmap item at a time unless instructed otherwise.

---

# 9. Before Implementing

Before changing code, determine where the change belongs:

- Domain
- Application
- Port
- Adapter
- Infrastructure
- Tests

If the requested change violates the architecture:

Stop.

Explain why.

Do not start coding.

---

# 10. Things You Must Never Do

Never:

- redesign the architecture
- rename packages
- introduce asyncio
- introduce dependency injection frameworks
- introduce service locators
- move responsibilities between layers
- duplicate business logic
- perform unnecessary refactoring
- commit automatically
- merge automatically
- change architecture.md unless requested
- add real sleeps to tests
- add real network calls to tests

Keep every change as small as possible.

Optimize for maintainability over cleverness.