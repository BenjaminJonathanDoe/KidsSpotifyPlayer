# AGENTS.md

# KidsSpotifyPlayer Engineering Handbook

This repository is a small, synchronous, event-driven application for a child-friendly Spotify player. The architecture exists to keep application decisions independent from hardware, JSON, and external services.

Treat this document as the canonical engineering guide for future implementations.

---

# Project philosophy

The architecture is intentionally simple and explicit.

- The application layer should make decisions, not talk to hardware or parse config files.
- Ports define capabilities. Adapters translate those capabilities to concrete technologies.
- Events are facts about what happened. They are immutable data, not behavior.
- The controller contains application decisions such as resolving an NFC card to a playback target.
- Configuration is hidden behind repositories so the rest of the application sees a stable interface, not JSON structures.
- The system is built for deterministic behavior and easy testing on non-hardware platforms.

---

# Architecture

The repository is organized into layers.

## Domain

The domain layer contains stable, platform-independent concepts.

Allowed:
- domain events
- domain models such as PlaybackTarget
- enums and simple value objects
- immutable data structures

Must never depend on:
- Raspberry Pi libraries
- Spotify SDKs
- JSON parsing
- hardware adapters
- infrastructure concerns

## Application

The application layer contains orchestration and decisions.

The current application entry points are:
- PlayerController
- Application composition root

Allowed:
- interpreting domain events
- calling ports
- making application-level decisions
- coordinating a synchronous flow of work

Must never depend on:
- GPIO, NFC hardware, LEDs, audio, or networking directly
- JSON files
- concrete adapter implementations

## Ports

Ports are protocols that describe capabilities the application needs.

Examples:
- SpotifyPlayer
- FeedbackOutput
- ConfigRepository

Rules:
- ports describe behavior, not implementation
- ports should stay narrow and focused
- application code depends on ports, not concrete classes

## Adapters

Adapters implement ports for a specific technology.

Examples:
- JSONConfigRepository for configuration
- future Spotify adapters
- future NFC or button adapters

Rules:
- adapters translate between external protocols and the domain/application contract
- adapters may parse JSON, open files, talk to hardware, or wrap SDKs
- adapters must not contain business logic
- adapters must not make application decisions beyond translation

## Infrastructure

Infrastructure owns technical concerns and wiring.

Current examples:
- EventBus
- InputCoordinator
- Application composition root

Rules:
- infrastructure is responsible for constructing and linking objects
- infrastructure keeps the application synchronous and deterministic
- infrastructure should not contain business rules

## Composition root

The composition root is the Application class.

It is responsible for:
- constructing the event bus
- constructing the input coordinator
- constructing the config repository
- constructing the controller
- registering handlers
- wiring concrete implementations supplied by the caller

The composition root owns the dependency graph for the current slice of the application.

---

# Dependency direction

Keep dependencies flowing inward.

- Domain is the core. It should not depend on application, ports, or adapters.
- Application depends on domain and ports.
- Adapters implement ports and may depend on domain, but they should not be depended on by domain.
- Infrastructure wires the graph together.

In short:

Domain <- Application <- Ports <- Adapters

Infrastructure sits above this graph and composes it.

---

# Design rules

Follow these rules in every change.

- Controllers never know JSON.
- Repositories never expose dictionaries as part of the application contract.
- Events are immutable facts. They do not contain behavior.
- Ports describe capabilities. They do not describe infrastructure details.
- Adapters translate protocols. They do not make business decisions.
- Application owns orchestration.
- Infrastructure owns technical concerns.
- No business logic belongs in adapters.
- No hardware knowledge belongs in application.
- No Spotify SDK or hardware integration should appear outside adapters.
- Keep the EventBus synchronous.
- Do not introduce async unless the task explicitly requires it.
- Avoid hidden magic, global state, and service locators.

---

# Testing strategy

Tests should reflect the architecture.

## Unit tests

Use unit tests for small, focused behavior.

Examples:
- domain models and events
- event bus dispatch
- input coordinator serialization
- repository validation logic

## Integration tests

Use integration tests when multiple components must work together.

Examples:
- Application wiring with real repository and controller
- event flow through the public input coordinator

## Acceptance tests

Use acceptance tests for the currently implemented application slice from a public input event to an observable port call.

These tests should:
- exercise the real application graph
- use public entry points
- verify observable behavior only
- avoid inspecting private state or helper methods

Prefer test-first additions for new behavior.

---

# Git workflow

Work on a dedicated feature branch.

Flow:

main
↓
feature branch
↓
implement
↓
review
↓
tests
↓
merge with --no-ff
↓
main stays green

Rules:
- do not work directly on main
- keep changes focused and related to the task
- run the full test suite before finishing
- review diffs for unrelated changes
- do not push or merge unless explicitly requested

---

# Code style

Follow the existing conventions in the repository.

- Python 3.11 syntax
- type hints everywhere
- dataclasses for immutable domain data
- Protocols for ports
- small modules and small classes
- explicit, readable names
- no premature abstractions
- prefer standard library over new dependencies
- prefer immutable values where practical
- avoid clever code and hidden side effects

Naming:
- modules and functions use snake_case
- classes use PascalCase
- events and models use descriptive names

Keep the implementation simple enough that a new engineer can read it quickly.

---

# Future features

New hardware should be added as an adapter implementing an existing port.

Examples:
- Spotify becomes a Spotify adapter implementing SpotifyPlayer
- NFC becomes an NFC adapter implementing the relevant input port
- Buttons become button adapters publishing neutral events
- LEDs become a feedback adapter
- Audio becomes an audio-output adapter
- Display, if added later, becomes another adapter behind a port

A concrete Spotify example of the layering is:

PlayerController
↓
SpotifyPlayer port
↓
SpotifyWebApiPlayer adapter
↓
Spotify API client
↓
librespot device on the Pi

The application talks to the port. The adapter translates that contract to the concrete Spotify stack. The controller never depends on the Spotify SDK or the Pi device directly.

Do not place hardware knowledge in the application layer.

---

# Non-goals

The project deliberately avoids:
- singletons
- global state
- service locators
- dependency injection frameworks
- hidden magic
- async unless clearly required
- polling inside controllers
- business logic inside adapters

---

# Implementation checklist

Before submitting code, verify all of the following:

- [ ] The change matches the existing architecture
- [ ] The change stays in the correct layer
- [ ] The public contract is preserved unless a real mismatch is being fixed
- [ ] New behavior is covered by tests
- [ ] Tests are written before or alongside the implementation
- [ ] The full test suite passes
- [ ] The diff is focused and free of unrelated edits
- [ ] No accidental production changes slipped in

If a requested change would force a major architectural shift, stop and explain the trade-off before implementing it.