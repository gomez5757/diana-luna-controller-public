# Diana GitHub-only bounded lifecycle controller

This repository contains only the small, reviewed lifecycle controller for one pre-existing Codespace. It never receives Diana+ source, private task prompts, Codex/ChatGPT authentication, worker output, or a token for the private repository.

## Contract

The coordinator writes `control/signal.json` with exactly three fields: integer `schema: 1`, `action`, and a new 32-character lowercase hexadecimal `nonce`. No commands, URLs, repository names, or machine identifiers are accepted from the signal. The target Codespace is fixed in the reviewed controller.

- `stop`: request shutdown and require the provider to report `Shutdown`.
- `probe`: start the installed private worker, allow a bounded 300-second lease, then stop and confirm shutdown.
- `wake`: the same lifecycle with a 900-second lease.

Wake/probe are gated by `control/installation.json`. They do not upload or execute model code in this public runner. The private Codespace independently validates its root-owned installation, protected authorization, queue, ownership, exact source hashes, and persisted receipts before starting any work.

## Safety

The only secret consumed here is the already-installed `DIANA_CODESPACE_LIFECYCLE_TOKEN`. The code calls the official start/stop endpoints for the fixed Codespace, rejects redirects and oversized replies, and prints only a sanitized lifecycle summary. Do not expand the signal schema or add private-source/authentication handling.

The token's provider permission is broader than the two endpoints used by this program; this repository does not claim that GitHub exposes an endpoint-specific two-method token.

All signals share one non-cancelling Actions concurrency group. The controller stops in `finally`; an additional `always()` workflow step requests and verifies shutdown. The job itself has a 20-minute ceiling. A successful workflow means lifecycle operations succeeded, **not** that a private coding task passed. Read the private task receipts and branch contents separately.

There is no recurring schedule. A committed signal or a manually requested workflow run is a one-off operation. Replaying a signal can restart the machine; the private worker's task ledger and receipts, not this nonce, prevent repeating completed model work.

## Cost boundary

Use standard public Ubuntu Actions runners only. Do not add paid runners, artifacts, external hosting, or billing changes. The owner's Codespaces product budget was verified at zero with `Stop usage` enabled; the private machine still consumes its included compute/storage quota, including storage while stopped. Reaching quota is a reason to stop, not to buy capacity or bypass the budget.

## Tests

`python3 -m unittest -v` runs the deterministic controller suite without credentials. It checks signal restrictions, shutdown observation, bounded wake duration, and stop-on-error behavior. These tests are not a substitute for the private end-to-end receipt.
