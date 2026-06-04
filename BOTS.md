# Runtime Registry

Canonical machine-readable registry: `bots.json`.

Every independently runnable app, bot, worker, script entrypoint, or live process
variant must be registered there before use. The registry is the source of truth
for runtime id/name, entrypoint path, notes paths, backlog path, session path,
and expected artifact names.

## Registered Runtimes

| Runtime id | Name | Runtime path | Notes scope |
| --- | --- | --- | --- |
| `daily-planner-app` | Daily Planner desktop app | `daily_planner.py` | `C:/Users/Cmcna/Dev/notes/projects/daily-planner` |

## Audit Tokens

- Use ISO-8601 local timestamps with offset, for example `2026-06-04T01:45:00-04:00`.
- Use `runtime: not-launched` when no process was started.
- Use `runtime: dry-run`, `runtime: watch-only`, `runtime: local`, `runtime: staging`, or `runtime: production` only when that runtime actually ran.
- Version/session entries must include runtime id, command, cwd, key env/flags, and verification, or explicitly say `runtime: not-launched`.

## Artifact Globs

This app persists user data to `C:/Users/Cmcna/daily_planner.json` (outside the
repo, by design — it is personal data, not a project artifact). The repo ships no
durable logs or ledgers, so `artifacts` is intentionally empty in `bots.json`.
