# Fails CI if VERSION is <= origin/main or collides with another open PR.
# Wired into .github/workflows/version-check.yml on pull_request.

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'version_helpers.ps1')

$repoRoot = Get-RepoRoot
$local = (Get-Content -LiteralPath (Join-Path $repoRoot 'VERSION')).Trim()
$master = Get-MasterVersion
$claimed = @(Get-OpenPRVersions)

$comparison = Compare-Versions $local $master
if ($comparison -eq 0) {
    Write-Error "VERSION ($local) matches origin/main - bump it via scripts/claim_version.ps1"
    exit 2
}
if ($comparison -lt 0) {
    Write-Error "VERSION ($local) is not greater than origin/main ($master) - re-run scripts/claim_version.ps1"
    exit 2
}
if ($claimed -contains $local) {
    Write-Error "VERSION ($local) is already claimed by another open PR - re-run scripts/claim_version.ps1"
    exit 3
}

Write-Output "VERSION $local is unique"
exit 0
