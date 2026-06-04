[CmdletBinding()]
param(
    [string]$Version = '',
    [Parameter(Mandatory = $true)]
    [string]$Slug,
    [Parameter(Mandatory = $true)]
    [string[]]$Details,
    [string[]]$Verification = @(),
    [string]$Commit = '',
    [string]$NotesPath = 'C:/Users/Cmcna/Dev/notes/projects/daily-planner/reference-version-history.md'
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ($NotesPath -match '<[^>]+>') {
    throw "NotesPath still contains template placeholders: $NotesPath"
}
$versionPath = Join-Path $repoRoot 'VERSION'
if ([string]::IsNullOrWhiteSpace($Version)) {
    if (-not (Test-Path -LiteralPath $versionPath)) {
        throw 'VERSION is missing; pass -Version explicitly or create VERSION first.'
    }
    $Version = (Get-Content -LiteralPath $versionPath -Raw).Trim()
}

if ($Version -notmatch '^\d+\.\d+\.\d+\.\d+$') {
    throw "Version must be four segments, got '$Version'"
}

if (-not (Test-Path -LiteralPath $NotesPath)) {
    throw "Notes-side version history not found: $NotesPath"
}

$timestamp = Get-Date -Format 'yyyy-MM-ddTHH:mm:sszzz'
$today = Get-Date -Format 'yyyy-MM-dd'
$entryHeader = "## $Version-$Slug - $today"
$text = Get-Content -LiteralPath $NotesPath -Raw

if ($text -match "(?m)^##\s+$([regex]::Escape($Version))(?=-|\s|$)") {
    Write-Output "Notes version history already has an entry for $Version."
    exit 0
}

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add($entryHeader)
$lines.Add('')
$lines.Add("- Timestamp: `$timestamp`.")
foreach ($detail in $Details) {
    if (-not [string]::IsNullOrWhiteSpace($detail)) {
        $lines.Add("- $detail")
    }
}
if (-not [string]::IsNullOrWhiteSpace($Commit)) {
    $lines.Add("- Local commit: ``$Commit``.")
}
if ($Verification.Count -gt 0) {
    $lines.Add("- Verification:")
    foreach ($item in $Verification) {
        if (-not [string]::IsNullOrWhiteSpace($item)) {
            $lines.Add("  - $item")
        }
    }
}
$lines.Add('')

$entry = ($lines -join "`r`n")
$headingRegex = [regex]'(?m)^## '
$updated = $headingRegex.Replace($text, "$entry`r`n## ", 1)
if ($updated -eq $text) {
    $updated = $text.TrimEnd() + "`r`n`r`n" + $entry
}

$updated = $updated -replace '(?m)^updated:\s+\d{4}-\d{2}-\d{2}\s*$', "updated: $today"
Set-Content -LiteralPath $NotesPath -Value $updated -NoNewline
Write-Output "Recorded notes-side version history entry for $Version."
