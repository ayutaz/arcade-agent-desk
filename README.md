# Arcade Agent Desk

A small desk display for jobs running on your computer. It shows **WORK, DONE,
FAIL, WAIT or LOST** on a Scratch Arcade handheld, with a short notification tone.
The computer sends status numbers, never command text, source code or full logs.

[日本語](README.ja.md)

## Current status

The authenticated protocol, command runner and C device app pass host tests.
The UDP bridge, pairing/build command, real-device trial and installation guide
are still being implemented. **This is not a device-tested release yet.**

## Run the tests

Install [uv](https://docs.astral.sh/uv/) and Clang, then:

```sh
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
```

Python is pinned to 3.12.13. Host tests need no GPU, credentials or connected device.
They compile the real C app with a mock OS and test real short-lived subprocesses.

## Design

- A 40-byte authenticated notification fits the OS's 64-byte UDP limit.
- A durable launch generation rejects packets from a previous app launch.
- Sequence numbers reject replay and reordering; expired messages show LOST.
- Up to four numbered tasks can be selected with the direction buttons.
- The host runner reports the actual exit status and bounds command execution.

The app targets the [Scratch Arcade OS](https://github.com/ayutaz/scratch-arcade-os)
ABI 2 SDK. Production pairing keys stay local and must not be committed.
The public test key is only a fixture, not a deployable pairing credential.

Development details: [host validation](docs/validation.md),
[protocol](docs/protocol.md). Code is licensed under [Apache-2.0](LICENSE).
