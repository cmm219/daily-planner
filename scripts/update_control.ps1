[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Runtime,
    [ValidateSet('version', 'note', 'start', 'end', 'backlog')]
    [string]$Event = 'note',
    [Parameter(Mandatory = $true)]
    [string]$Summary,
    [ValidateSet('not-launched', 'dry-run', 'watch-only', 'local', 'staging', 'production')]
    [string]$RuntimeState = 'not-launched',
    [string]$Command = 'not run',
    [string]$RunCwd = '',
    [string[]]$Env = @(),
    [string]$Verification = '',
    [string]$StopReason = '',
    [string]$BacklogItem = '',
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$registryPath = Join-Path $repoRoot 'bots.json'
if (-not (Test-Path -LiteralPath $registryPath)) {
    throw "Missing runtime registry: $registryPath"
}

$registry = Get-Content -LiteralPath $registryPath -Raw | ConvertFrom-Json
$runtimeConfig = @($registry.bots | Where-Object { $_.id -eq $Runtime })[0]
if ($null -eq $runtimeConfig) {
    $known = ($registry.bots | ForEach-Object { $_.id }) -join ', '
    throw "Unknown runtime '$Runtime'. Register it in bots.json first. Known runtimes: $known"
}

if ($Event -eq 'end' -and [string]::IsNullOrWhiteSpace($StopReason)) {
    throw "Event 'end' requires -StopReason."
}

$dirty = -not [string]::IsNullOrWhiteSpace((git -C $repoRoot status --porcelain))
if ($Event -eq 'start' -and $RuntimeState -in @('production') -and $dirty) {
    throw "Refusing to log production start from a dirty worktree."
}

if (-not (Test-Path -LiteralPath $registry.notes_root)) {
    throw "Notes root does not exist: $($registry.notes_root)"
}
$notesRoot = (Resolve-Path $registry.notes_root).Path

$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
$date = Get-Date -Format "yyyy-MM-dd"
$slug = ($Summary.ToLowerInvariant() -replace '[^a-z0-9]+', '-' -replace '(^-|-$)', '')
if ([string]::IsNullOrWhiteSpace($slug)) { $slug = $Event }
if ($slug.Length -gt 48) { $slug = $slug.Substring(0, 48).Trim('-') }

$versionPath = Join-Path $repoRoot 'VERSION'
$version = if (Test-Path -LiteralPath $versionPath) { (Get-Content -LiteralPath $versionPath -Raw).Trim() } else { 'unknown' }
$sha = (git -C $repoRoot rev-parse --short HEAD).Trim()
$branch = (git -C $repoRoot rev-parse --abbrev-ref HEAD).Trim()
$operator = if ($env:USERNAME) { $env:USERNAME } else { [Environment]::UserName }
$hostname = [Environment]::MachineName
$runCwdValue = if ([string]::IsNullOrWhiteSpace($RunCwd)) { $repoRoot } else { $RunCwd }
$envText = if ($Env.Count -gt 0) { $Env -join '; ' } else { 'not recorded' }
$verificationText = if ([string]::IsNullOrWhiteSpace($Verification)) { 'not recorded' } else { $Verification }
$stopText = if ([string]::IsNullOrWhiteSpace($StopReason)) { 'not applicable' } else { $StopReason }

$sessionsDir = Join-Path $notesRoot $runtimeConfig.sessions_dir
$backlogPath = Join-Path $notesRoot $runtimeConfig.backlog_file
$statePath = Join-Path $notesRoot $runtimeConfig.state_file
New-Item -ItemType Directory -Force -Path $sessionsDir | Out-Null

$sessionPath = Join-Path $sessionsDir "$date-$($timestamp.Substring(11,2))$($timestamp.Substring(14,2))-$($Runtime.ToLowerInvariant())-$Event-$slug.md"
$relativeSession = $sessionPath.Replace($notesRoot + '\', '').Replace('\', '/')

$lines = @(
    '---',
    "project: $($registry.project)",
    "runtime: $Runtime",
    "event: $Event",
    "timestamp: $timestamp",
    "version: $version",
    "runtime_state: $RuntimeState",
    '---',
    '',
    "# $Summary",
    '',
    "- Timestamp: $timestamp",
    "- Runtime: $Runtime ($($runtimeConfig.name))",
    "- Event: $Event",
    "- Version: $version",
    "- Runtime state: $RuntimeState",
    "- Command: ``$Command``",
    "- Cwd: ``$runCwdValue``",
    "- Env/deploy/live flags: $envText",
    "- Git: branch ``$branch``, sha ``$sha``, dirty=$dirty",
    "- Host/operator: $hostname / $operator",
    "- Verification: $verificationText",
    "- Stop reason: $stopText"
)

if ($DryRun) {
    Write-Output "DRY RUN would write session: $sessionPath"
} else {
    Set-Content -LiteralPath $sessionPath -Value ($lines -join "`r`n")
}

if (-not [string]::IsNullOrWhiteSpace($BacklogItem) -or $Event -eq 'backlog') {
    $item = if ([string]::IsNullOrWhiteSpace($BacklogItem)) { $Summary } else { $BacklogItem }
    $backlogLine = "- [ ] $timestamp ``$Runtime`` $item"
    if ($DryRun) {
        Write-Output "DRY RUN would append backlog: $backlogPath"
    } else {
        Add-Content -LiteralPath $backlogPath -Value $backlogLine
    }
}

if (Test-Path -LiteralPath $statePath) {
    $pointer = @"
<!-- audit-pointer:start -->
## Latest Audit Pointer

- $timestamp ``$Event`` ``$Runtime`` ``$version`` runtime: ``$RuntimeState`` -> ``$relativeSession``
<!-- audit-pointer:end -->
"@
    $state = Get-Content -LiteralPath $statePath -Raw
    $pattern = '(?ms)<!-- audit-pointer:start -->.*?<!-- audit-pointer:end -->'
    if ($state -match $pattern) {
        $auditPointerRegex = [regex]::new($pattern)
        $updated = $auditPointerRegex.Replace($state, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $pointer }, 1)
    } elseif ($state -match '(?m)^## Startup Pointers') {
        $updated = $state -replace '(?m)^## Startup Pointers', "$pointer`r`n`r`n## Startup Pointers"
    } else {
        $updated = $state.TrimEnd() + "`r`n`r`n$pointer`r`n"
    }
    if ($DryRun) {
        Write-Output "DRY RUN would update state pointer: $statePath"
    } else {
        Set-Content -LiteralPath $statePath -Value $updated
    }
}

Write-Output "Audit event recorded for $Runtime at $relativeSession"
