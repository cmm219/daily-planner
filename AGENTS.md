# daily-planner — Agent Instructions

## Start Here

Read only these at session start:

- `C:/Users/Cmcna/Dev/notes/projects/daily-planner/control/STATE.md`
- `C:/Users/Cmcna/Dev/notes/projects/daily-planner/control/TASKS.md`

Read `control/CODEX_GUARDRAILS.md` before non-trivial edits, risky work, or data changes.

## Hard Rules

- Notes-vault control files are authoritative.
- Keep startup/control files short.
- Move open/deferred work to `tasks/backlog.md`, plans to `tasks/audits/`, completed work to `tasks/archive/YYYY-MM-done.md`, and session history to `sessions/` (all under `C:/Users/Cmcna/Dev/notes/projects/daily-planner/`).
- Use normal work for small safe tasks. Use `tasks/audits/` only when work needs a review gate. Plans with `status: review-needed` must not be implemented until reviewed.
- Branch from `origin/main`, never local `main`, when making repo changes.
- Use a first-class project root for standalone systems.
- Never touch another agent's branch, worktree, or PR.
- Bump `VERSION` via `scripts/claim_version.ps1` only. Never hand-edit.
- Every edit batch must have the full audit path before handoff: `VERSION`
  bumped via `scripts/claim_version.ps1`, `CHANGELOG.md` updated,
  notes-side `reference-version-history.md` updated via
  `scripts/record_project_version.ps1`, a timestamped session/control pointer
  written via `scripts/update_control.ps1`, and verification recorded.
- Every shipped PR includes `VERSION`, `CHANGELOG.md`, and audit-note updates in
  the same commit as the code/docs change.
- Every independently runnable app/script entrypoint must be registered in
  `bots.json`; `BOTS.md` explains runtime ids and valid runtime tokens.
- Valid runtime tokens are `runtime: not-launched`, `runtime: dry-run`,
  `runtime: watch-only`, `runtime: local`, `runtime: staging`, and
  `runtime: production`; use `runtime: not-launched` when no process was started.
- Keep open/deferred work in `tasks/backlog.md`; control files are current-state
  pointers only.
- The personal data file `C:/Users/Cmcna/daily_planner.json` is user data: never
  delete, truncate, or migrate its schema without an explicit backup and same-turn
  user confirmation.
- Versions use `major.minor.patch.micro`; this project starts at `0.1.0.0`, with
  `1.0.0.0` reserved for the first stable/public release.
- Verify before claiming done.

## Bootstrap Verification

After setup changes, before commit:

1. Run `scripts/check_project_scaffold.ps1`.
2. Confirm there are no unresolved placeholders in `AGENTS.md`, `CLAUDE.md`, `bots.json`, `BOTS.md`, or copied scripts.
3. Run `scripts/check_control_hygiene.ps1`.
4. Run PowerShell parser checks for copied scripts.
5. Run `scripts/check_version_unique.ps1` once a GitHub remote exists and PRs ship.

## Batch Autonomy

When the user approves a task list with "do it all", "keep going", "finish this", "ship it", or equivalent, treat the approved list as one batch scope. Continue to the next approved item automatically after verification. Each PR must map to an approved item; stop before inventing new scope. Control/session/archive updates happen at batch end unless there is a real blocker.

Stop only for secrets/access, destructive or irreversible operations outside scope, unclear product/data risk, conflicting instructions, or full batch completion.

## Local

Run `python daily_planner.py` (needs `flet`). A desktop window opens; data
persists to `C:/Users/Cmcna/daily_planner.json`. No fixed ports, no background
singleton processes.

## Don't-Drag-Names Guard

- Use the setup playbook as the source. Do not inspect older projects unless the user explicitly asks for a specific comparison.
- Read prior-project files as structural templates only.
- Strip every literal name, path, port, service name, brand, or vault path that does not belong to this project.
