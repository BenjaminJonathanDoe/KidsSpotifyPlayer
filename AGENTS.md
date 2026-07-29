# AGENTS.md

# KidsSpotifyPlayer Development Guide

This document defines the engineering standards, architecture, and workflow for all AI agents working on this repository.

The goal is not only to produce working code, but to produce maintainable, testable and well-designed software.

---

# Project Goal

KidsSpotifyPlayer is a child-friendly Spotify player running on a Raspberry Pi Zero 2 W.

The player is controlled using

- NFC cards
- physical buttons
- LED feedback

The software must remain modular enough that an ESP32 can later become a remote input controller without requiring architectural changes.

---

# Architecture

Before implementing any feature, always read:

- docs/architecture.md

Follow the architecture exactly unless explicitly instructed otherwise.

Important principles:

- Application logic must never depend on Raspberry Pi libraries.
- Hardware-specific code belongs only inside adapters.
- The Domain layer must be completely platform independent.
- The Application layer depends only on Domain and Ports.
- Adapters implement Ports.
- Keep the EventBus synchronous.
- Input adapters are lifecycle-controlled event sources that publish neutral domain events; do not design input ports as polling interfaces.
- Do not introduce asyncio unless explicitly requested.
- Do not introduce a dependency injection framework.
- Runtime persistence is intentionally avoided.
- Secrets and credentials must never be committed.

---

# Engineering Principles

Prefer:

- simplicity
- readability
- deterministic behaviour
- explicit code
- small focused classes
- composition over inheritance
- testability
- maintainability

Avoid:

- premature optimization
- unnecessary abstractions
- unnecessary asynchronous code
- unnecessary dependencies
- magic behaviour
- hidden side effects

If a solution can be both simpler and equally maintainable, choose the simpler one.

---

# Design Review Before Implementation

Before implementing a feature:

1. Review the existing implementation.
2. Review the relevant architecture.
3. Verify consistency with:
   - architecture.md
   - existing APIs
   - previous architectural decisions

If you believe the requested implementation introduces an architectural problem:

- DO NOT modify any files.
- Explain the concern.
- Propose alternatives.
- Explain the trade-offs.
- Wait for approval.

Never redesign the architecture without explicit approval.

---

# Scope Discipline

Implement only the requested task.

Do not:

- refactor unrelated code
- rename unrelated files
- introduce new abstractions without justification
- add dependencies unless requested

If you identify additional improvements:

Finish the requested work first.

Then list the suggested improvements separately without implementing them.

---

# Python Guidelines

Use:

- Python 3.11 compatible syntax
- type hints everywhere
- dataclasses where appropriate
- Protocol for interfaces
- Enum where appropriate
- standard library whenever possible

Keep modules small.

Avoid classes that exceed roughly one responsibility.

---

# Event System

The EventBus is intentionally simple.

Rules:

- synchronous dispatch
- no queues
- no asyncio
- no retries
- no inheritance-based dispatch
- exceptions propagate
- deterministic execution order

The EventBus is infrastructure, not business logic.

---

# Testing

Every feature should include appropriate tests.

Before committing:

Run:

python -m pytest -q

Do not consider the task complete until the tests pass.

Avoid meaningless tests.

Tests should verify behaviour rather than implementation details whenever practical.

---

# Git Workflow

Never develop directly on main.

Always verify the current branch before making changes.

If the current branch is main:

STOP.

Do not modify files.

Feature work must happen on dedicated branches.

Branch naming:

feature/<name>
fix/<name>
docs/<name>
chore/<name>

Do not:

- merge into main
- force push
- rewrite history
- use git reset --hard

Commit only files related to the current task.

Run tests before committing.

Run:

git diff --check

before every commit.

Create a single focused commit unless instructed otherwise.

Commit messages should use the imperative mood.

Example:

Add synchronous event bus

After committing report:

- branch
- commit hash
- commit message
- changed files
- test result

Do not push unless explicitly requested.

---

# Development Environment

Always use the project's local virtual environment.

Never use global Python.

Always execute Python commands as:

python -m ...

Never use:

pip install ...

Use:

python -m pip install ...

Before executing commands verify:

python --version

python -m pip --version

where python

The interpreter must point to:

.venv

If not, stop and explain the problem.

Never install packages outside the project virtual environment.

If a required package is missing:

Report it before installing.

---

# Context Usage

Read only the files required for the current task.

Do not scan the entire repository unless explicitly requested.

Minimize context usage.

Prefer many small focused tasks over large refactorings.

---

# Coding Style

Prefer explicit code.

Avoid clever code.

Prefer readable names over short names.

Public APIs should be stable.

Document non-obvious decisions.

Avoid comments that merely repeat the code.

---

# Architecture Decision Records

When an implementation introduces a new architectural decision:

Do not immediately implement it.

Instead propose creating an ADR in:

docs/decisions/

Example:

001-event-bus.md

Each ADR should include:

- Decision
- Context
- Alternatives
- Consequences

---

# When Unsure

If requirements are ambiguous:

Stop.

Explain the ambiguity.

Offer alternatives.

Wait for approval.

Never guess architectural decisions.

---

# Definition of Done

A task is complete only when:

✓ Scope implemented

✓ Architecture respected

✓ Tests pass

✓ No unrelated files modified

✓ No unnecessary dependencies added

✓ git diff --check passes

✓ Commit created

✓ Summary provided

Working code is not sufficient.

Maintainable code is the goal.