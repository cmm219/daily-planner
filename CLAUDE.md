# daily-planner

A paper-style daily planner desktop app (Flet/Python) with multi-day tabs, dynamic rows, task archiving, and reflections.

## Start Here

Read only these at session start:

- `C:/Users/Cmcna/Dev/notes/projects/daily-planner/control/STATE.md`
- `C:/Users/Cmcna/Dev/notes/projects/daily-planner/control/TASKS.md`

Read `control/CODEX_GUARDRAILS.md` before non-trivial edits, risky work, deploys, or data changes.

## Notes Config

project: daily-planner
write_path: C:/Users/Cmcna/Dev/notes/projects/daily-planner

Use the setup playbook as the source. Do not inspect older projects unless the user explicitly asks for a specific comparison.

## Hard Rules

- Notes-vault control files are authoritative.
- Keep `STATE.md` and `TASKS.md` short.
- Move open/deferred work to `C:/Users/Cmcna/Dev/notes/projects/daily-planner/tasks/backlog.md`, plans to `C:/Users/Cmcna/Dev/notes/projects/daily-planner/tasks/audits/`, completed work to `C:/Users/Cmcna/Dev/notes/projects/daily-planner/tasks/archive/YYYY-MM-done.md`, and session history to `C:/Users/Cmcna/Dev/notes/projects/daily-planner/sessions/`.
- Use normal work for small safe tasks. Use `tasks/audits/` only when work needs a review gate: risky changes, broad refactors, parallel Codex/Claude work, PR/version/deploy coordination, data impact, or anything where one agent should review before another implements. Plans with `status: review-needed` must not be implemented until reviewed.
- Branch from `origin/main`, not local `main`, when making repo changes.
- Use a first-class project root for standalone systems. Worktrees are optional isolation for concurrent/risky edits, not the default home for every new effort.
- Never touch another agent's branch, worktree, or PR.
- Bump `VERSION` only with `scripts/claim_version.ps1`; never hand-edit it.
- Every edit batch must have the full audit path before handoff: `VERSION`
  bumped via `scripts/claim_version.ps1`, `CHANGELOG.md` updated,
  notes-side `reference-version-history.md` updated via
  `scripts/record_project_version.ps1`, a timestamped session/control pointer
  written via `scripts/update_control.ps1`, and verification recorded. Docs,
  comments, tests, scripts, monitor-only edits, and tiny cleanup are not exempt.
- Every shipped PR includes `VERSION`, `CHANGELOG.md`, and audit-note updates in
  the same commit as the code/docs change.
- Every independently runnable app/script entrypoint must be registered in
  `bots.json`; `BOTS.md` explains runtime ids and valid runtime tokens.
- Valid runtime tokens are `runtime: not-launched`, `runtime: dry-run`,
  `runtime: watch-only`, `runtime: local`, `runtime: staging`, and
  `runtime: production`; use `runtime: not-launched` when no process was started.
- Keep open/deferred work in `tasks/backlog.md`; control files are current-state
  pointers only.
- This app writes a personal data file at `C:/Users/Cmcna/daily_planner.json`.
  Treat it as user data: never delete, truncate, or rewrite its schema without
  an explicit backup and user confirmation in the same turn.
- Verify before claiming done.

## Batch Autonomy

When the user approves a task list with "do it all", "keep going", "finish this", "ship it", or equivalent, treat the approved list as one batch scope.

Inside a batch:
- Multiple PRs may be used. Individual PR merge is not a stop condition.
- Continue to the next approved item automatically after verification.
- Each PR must map to an approved item; stop before inventing new scope.
- Control/session/archive updates happen at batch end unless there is a real blocker, handoff, or interruption.

Stop only for secrets/access, destructive or irreversible operations outside scope, unclear product/data risk, conflicting instructions, or full batch completion.

## Version Policy

Versions use `major.minor.patch.micro`. This project starts at `0.1.0.0`; reserve `1.0.0.0` for the first stable/public release.

## Bootstrap Verification

After setup changes, before commit:

1. Run `scripts/check_project_scaffold.ps1`.
2. Confirm there are no unresolved placeholders in `AGENTS.md`, `CLAUDE.md`, `bots.json`, `BOTS.md`, or copied scripts.
3. Run `scripts/check_control_hygiene.ps1`.
4. Run PowerShell parser checks for copied scripts.
5. Run `scripts/check_version_unique.ps1` once a GitHub remote exists and PRs ship.

## Deploy

No external deploy. This is a local desktop app.

## Local

Run `python daily_planner.py` (needs `flet`, see `requirements.txt`). A desktop
window opens; data persists to `C:/Users/Cmcna/daily_planner.json`. Flet may bind
an ephemeral local port for its internal web view — no fixed port to reserve. No
background jobs, schedulers, or singleton live processes.
