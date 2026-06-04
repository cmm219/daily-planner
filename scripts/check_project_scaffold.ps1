# Lightweight bootstrap/handoff checks for copied setup templates.
# Keep this small. Project-specific tests belong in the project's normal test suite.

[CmdletBinding()]
param(
    [string]$RepoRoot,
    [string]$NotesRoot = 'C:/Users/Cmcna/Dev/notes/projects/daily-planner',
    [switch]$SkipVersionUnique
)

# Note: under Windows PowerShell 5.1, $PSScriptRoot is empty inside a param()
# default when [CmdletBinding()] is present, so resolve RepoRoot in the body.
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

$ErrorActionPreference = 'Stop'
$failed = $false

function Report-Failure {
    param([string]$Message)
    Write-Host "ERROR $Message" -ForegroundColor Red
    $script:failed = $true
}

function Test-NoPlaceholders {
    param([string[]]$Paths)

    foreach ($path in $Paths) {
        if (-not (Test-Path -LiteralPath $path)) { continue }
        $matchResults = Select-String -LiteralPath $path -Pattern '<[A-Z_][A-Z0-9_]+>' -ErrorAction SilentlyContinue
        foreach ($match in $matchResults) {
            Report-Failure "Placeholder remains in ${path}:$($match.LineNumber): $($match.Line.Trim())"
        }
    }
}

$requiredRepoFiles = @(
    'AGENTS.md',
    'CLAUDE.md',
    'VERSION',
    'CHANGELOG.md',
    'bots.json',
    'BOTS.md',
    'scripts/claim_version.ps1',
    'scripts/record_project_version.ps1',
    'scripts/update_control.ps1',
    'scripts/check_control_hygiene.ps1'
)

foreach ($rel in $requiredRepoFiles) {
    $path = Join-Path $RepoRoot $rel
    if (-not (Test-Path -LiteralPath $path)) {
        Report-Failure "Required scaffold file missing: $rel"
    }
}

$versionPath = Join-Path $RepoRoot 'VERSION'
if (Test-Path -LiteralPath $versionPath) {
    $version = (Get-Content -LiteralPath $versionPath -Raw).Trim()
    if ($version -notmatch '^\d+\.\d+\.\d+\.\d+$') {
        Report-Failure "VERSION must be major.minor.patch.micro, got '$version'"
    }

    $changelogPath = Join-Path $RepoRoot 'CHANGELOG.md'
    if ((Test-Path -LiteralPath $changelogPath) -and -not ((Get-Content -LiteralPath $changelogPath -Raw) -match "(?m)^## \[$([regex]::Escape($version))\]")) {
        Report-Failure "CHANGELOG.md does not contain current VERSION $version"
    }
}

$registryPath = Join-Path $RepoRoot 'bots.json'
if (Test-Path -LiteralPath $registryPath) {
    try {
        $registry = Get-Content -LiteralPath $registryPath -Raw | ConvertFrom-Json
        if (-not $registry.project) { Report-Failure 'bots.json missing project' }
        if (-not $registry.notes_root) { Report-Failure 'bots.json missing notes_root' }
        if (-not $registry.bots -or @($registry.bots).Count -lt 1) { Report-Failure 'bots.json must register at least one runtime' }
        foreach ($runtime in @($registry.bots)) {
            if (-not $runtime.id -or $runtime.id -match '<[^>]+>') { Report-Failure 'bots.json has missing or placeholder runtime id' }
            if (-not $runtime.runtime_path -or $runtime.runtime_path -match '<[^>]+>') { Report-Failure "bots.json runtime '$($runtime.id)' has missing/placeholder runtime_path" }
        }
    } catch {
        Report-Failure "bots.json is not valid JSON: $($_.Exception.Message)"
    }
}

$scriptPaths = @(
    'scripts/claim_version.ps1',
    'scripts/record_project_version.ps1',
    'scripts/update_control.ps1',
    'scripts/check_control_hygiene.ps1'
) | ForEach-Object { Join-Path $RepoRoot $_ }

foreach ($scriptPath in $scriptPaths) {
    if (-not (Test-Path -LiteralPath $scriptPath)) { continue }
    $tokens = $null
    $errors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$tokens, [ref]$errors) > $null
    if ($errors.Count -gt 0) {
        Report-Failure "PowerShell parse errors in ${scriptPath}: $($errors[0].Message)"
    }
}

Test-NoPlaceholders -Paths @(
    (Join-Path $RepoRoot 'AGENTS.md'),
    (Join-Path $RepoRoot 'CLAUDE.md'),
    (Join-Path $RepoRoot 'bots.json'),
    (Join-Path $RepoRoot 'BOTS.md')
)

$controlCheck = Join-Path $RepoRoot 'scripts/check_control_hygiene.ps1'
if (Test-Path -LiteralPath $controlCheck) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $controlCheck -NotesRoot $NotesRoot
    if ($LASTEXITCODE -ne 0) { Report-Failure 'check_control_hygiene.ps1 failed' }
}

if (-not $SkipVersionUnique) {
    $versionUnique = Join-Path $RepoRoot 'scripts/check_version_unique.ps1'
    if (Test-Path -LiteralPath $versionUnique) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $versionUnique
        if ($LASTEXITCODE -ne 0) { Report-Failure 'check_version_unique.ps1 failed' }
    }
}

if ($failed) { exit 1 }
Write-Host 'Project scaffold checks passed.'
