# Validates that control/ pointer files stay short and don't accumulate journal-style content.

param(
    [string]$NotesRoot = "C:/Users/Cmcna/Dev/notes/projects/daily-planner"
)

$ErrorActionPreference = "Stop"

$state = Join-Path $NotesRoot "control/STATE.md"
$tasks = Join-Path $NotesRoot "control/TASKS.md"
$guardrails = Join-Path $NotesRoot "control/CODEX_GUARDRAILS.md"

$limits = @(
    @{ Path = $state; Name = "STATE.md"; MaxLines = 60 },
    @{ Path = $tasks; Name = "TASKS.md"; MaxLines = 60 },
    @{ Path = $guardrails; Name = "CODEX_GUARDRAILS.md"; MaxLines = 80 }
)

$failed = $false

foreach ($item in $limits) {
    if (-not (Test-Path $item.Path)) {
        Write-Error "$($item.Name) missing at $($item.Path)"
        $failed = $true
        continue
    }

    $lines = @(Get-Content -LiteralPath $item.Path)
    $count = $lines.Count
    if ($count -gt $item.MaxLines) {
        Write-Error "$($item.Name) has $count lines; limit is $($item.MaxLines). Move open/deferred work to tasks/backlog.md, plans to tasks/audits/, completed work to tasks/archive/YYYY-MM-done.md, session history to sessions/, and deploy history to reference-version-history.md."
        $failed = $true
    } else {
        Write-Host "OK $($item.Name): $count/$($item.MaxLines) lines"
    }
}

$tasksText = Get-Content -Raw -LiteralPath $tasks
$focusMatches = [regex]::Matches($tasksText, "(?m)^- \*\*")
if ($focusMatches.Count -gt 5) {
    Write-Error "TASKS.md has $($focusMatches.Count) bold task/watch bullets; keep 3-5 total."
    $failed = $true
} else {
    Write-Host "OK TASKS.md focus/watch bullets: $($focusMatches.Count)/5"
}

$blockedHeadings = @("## Recent Notes", "## Recently Done")
foreach ($heading in $blockedHeadings) {
    foreach ($file in @($state, $tasks)) {
        if ((Get-Content -Raw -LiteralPath $file).Contains($heading)) {
            Write-Error "$(Split-Path $file -Leaf) contains '$heading'; control files should link detail files, not journal history."
            $failed = $true
        }
    }
}

if ($failed) { exit 1 }
Write-Host "Control hygiene passed."
