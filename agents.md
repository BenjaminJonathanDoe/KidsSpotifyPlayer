# KidsSpotifyPlayer Development Instructions

## Project goal

Build a child-friendly Spotify player running on a Raspberry Pi Zero 2 W.

The player is controlled by NFC cards and physical buttons and provides visual feedback through LEDs.

## Architecture

Before making architectural changes, read:

- `docs/architecture.md`

Follow the ports-and-adapters architecture described there.

Important rules:

- Application logic must not depend on Raspberry Pi libraries.
- Hardware-specific code belongs only in adapters.
- Domain models and application logic must run on Windows.
- Use neutral events for input and system behavior.
- Keep the initial event bus synchronous.
- Use fake adapters for automated tests.
- Do not introduce `asyncio` unless explicitly requested.
- Do not introduce a dependency injection framework.
- Do not add runtime persistence unless explicitly requested.
- Do not store credentials, tokens, or secrets in Git.

## Python rules

- Use Python 3.11-compatible syntax.
- Use type hints.
- Prefer standard-library features.
- Keep modules small and focused.
- Use dataclasses where appropriate.
- Write tests with pytest.
- Do not add dependencies without explaining why they are needed.

## Working method

- Read the relevant files before editing.
- Make focused changes only.
- Do not modify unrelated files.
- Explain significant decisions.
- Run relevant tests after changes.
- Show a summary of changed files.
- Never run destructive commands without explicit approval.

## Development Environment

Always use the project's local virtual environment.

Python interpreter:
- .venv/Scripts/python.exe (Windows)

Install Python packages only into the local virtual environment.

Always execute Python commands as:

python -m ...

Never use:
- global Python
- system pip
- user site packages

Before running tests, verify the interpreter by executing:

python --version
python -m pip --version

All tests must be executed in the local virtual environment.