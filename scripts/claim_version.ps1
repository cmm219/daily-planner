# Claims the next monotonic version above origin/main + all open PR VERSIONs.
# Writes VERSION and seeds a CHANGELOG.md stub. The ONLY way to bump VERSION.

[CmdletBinding()]
param(
    [ValidateSet('micro', 'patch', 'minor', 'major')]
    [string]$Type = 'micro',
    [string]$Slug = '',
    [switch]$DryRun,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

if ($Help) {
    Write-Output "Usage: claim_version.ps1 -Type [micro|patch|minor|major] [-Slug name] [-DryRun]"
    exit 0
}

. (Join-Path $PSScriptRoot 'version_helpers.ps1')

function Add-ChangelogStub {
    param([string]$RepoRoot, [string]$Version)

    $changelogPath = Join-Path $RepoRoot 'CHANGELOG.md'
    if (-not (Test-Path -LiteralPath $changelogPath)) { return }
    $changelog = Get-Content -LiteralPath $changelogPath -Raw
    if ($changelog -match "(?m)^## \[$([regex]::Escape($Version))\]") {
        return
    }

    $today = Get-Date -Format 'yyyy-MM-dd'
    $slugText = if ([string]::IsNullOrWhiteSpace($Slug)) { 'fill in description' } else { $Slug }
    $stub = "## [$Version] - $today`r`n`r`n### Changed`r`n- <!-- claimed by claim_version.ps1: $slugText -->`r`n`r`n"

    $pattern = '(?ms)(^## \[Unreleased\][^\r\n]*(?:\r?\n).*?)(?=^## \[)'
    if ($changelog -match $pattern) {
        $changelog = [regex]::Replace($changelog, $pattern, "`$1$stub", 1)
    } else {
        $changelog = $changelog -replace '(?m)^## \[Unreleased\][^\r\n]*\r?\n', "## [Unreleased]`r`n`r`n$stub"
    }
    Set-Content -LiteralPath $changelogPath -Value $changelog -NoNewline
}

$master = Get-MasterVersion
$claimed = @(Get-OpenPRVersions)
$base = Max-Version -Versions (@($master) + $claimed)
$candidate = Bump-Version -Current $base -BumpType $Type

if (-not $DryRun) {
    $repoRoot = Get-RepoRoot
    Set-Content -LiteralPath (Join-Path $repoRoot 'VERSION') -Value $candidate -NoNewline
    Add-ChangelogStub -RepoRoot $repoRoot -Version $candidate
}

Write-Output $candidate
exit 0
