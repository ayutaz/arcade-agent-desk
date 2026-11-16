# Development rules

- Read git status and this file before changes. Protect unrelated work.
- Use uv and Python 3.12.13; no pip or manual venv.
- Use TDD: behavioral test, intended Red, minimal implementation, Green, regression. Record commands/results in Japanese docs.
- Keep README.md in English and README.ja.md synchronized. Distinguish host, target build, device and human checks.
- Never commit credentials, identifiers, recordings or raw device logs. Production pairing keys are local-only.
- Device app changes require owned IDs/hashes and preserved existing apps. New firmware/Flash, eFuse, security or unknown GPIO operations require a concrete review and explicit permission.
- Do not disable scratch-arcade-os Flash guards or branch protections. Shared OS changes go through a PR and required CI.
- Commit coherent validated changes and push. No force-push or history rewriting.
