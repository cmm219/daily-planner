# Version helper functions shared by claim_version.ps1 and check_version_unique.ps1.
# Default branch: main

$ErrorActionPreference = 'Stop'

function Get-RepoRoot {
    $root = (& git rev-parse --show-toplevel 2>$null)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($root)) {
        throw "Not inside a git repository"
    }
    return $root.Trim()
}

function Read-VersionFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    $content = (Get-Content -LiteralPath $Path -Raw).Trim()
    if ([string]::IsNullOrWhiteSpace($content)) { return $null }
    return $content
}

function Get-MasterVersion {
    $repoRoot = Get-RepoRoot
    $versionPath = Join-Path $repoRoot 'VERSION'
    # Try origin/main first, fall back to local main, then HEAD VERSION.
    # Native git stderr can trip $ErrorActionPreference='Stop', so soften it
    # locally and verify the ref exists before reading it.
    $candidates = @('origin/main:VERSION', 'main:VERSION')
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        foreach ($ref in $candidates) {
            & git cat-file -e $ref 2>$null
            if ($LASTEXITCODE -ne 0) { continue }
            $output = (& git show $ref 2>$null)
            if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($output)) {
                return $output.Trim()
            }
        }
    } finally {
        $ErrorActionPreference = $prev
    }
    return Read-VersionFile -Path $versionPath
}

function Get-OpenPRVersions {
    # Returns array of VERSION strings claimed by other open PRs, via gh CLI.
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { return @() }
    $repoRoot = Get-RepoRoot
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        # No remote => no PRs to consider (and gh/git would error).
        $remotes = (& git -C $repoRoot remote 2>$null)
        if ([string]::IsNullOrWhiteSpace(($remotes -join ''))) { return @() }
        $currentBranch = (& git -C $repoRoot rev-parse --abbrev-ref HEAD 2>$null).Trim()
        $prs = & gh pr list --state open --json number,headRefName --jq '.[] | "\(.number)|\(.headRefName)"' 2>$null
        if ($LASTEXITCODE -ne 0) { return @() }
    } finally {
        $ErrorActionPreference = $prev
    }
    $versions = @()
    foreach ($line in $prs) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $parts = $line -split '\|', 2
        $branch = $parts[1]
        if ($branch -eq $currentBranch) { continue }
        $output = (& git show "origin/${branch}:VERSION" 2>$null)
        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($output)) {
            $versions += $output.Trim()
        }
    }
    return $versions
}

function Parse-Version {
    param([string]$Version)
    $parts = $Version -split '\.'
    $nums = @()
    foreach ($p in $parts) {
        $n = 0
        if (-not [int]::TryParse($p, [ref]$n)) {
            throw "Invalid version segment '$p' in '$Version'"
        }
        $nums += $n
    }
    while ($nums.Count -lt 4) { $nums += 0 }
    return $nums
}

function Compare-Versions {
    param([string]$A, [string]$B)
    $aa = Parse-Version $A
    $bb = Parse-Version $B
    for ($i = 0; $i -lt 4; $i++) {
        if ($aa[$i] -lt $bb[$i]) { return -1 }
        if ($aa[$i] -gt $bb[$i]) { return 1 }
    }
    return 0
}

function Max-Version {
    param([string[]]$Versions)
    $max = $null
    foreach ($v in $Versions) {
        if ([string]::IsNullOrWhiteSpace($v)) { continue }
        if ($null -eq $max -or (Compare-Versions $v $max) -gt 0) {
            $max = $v
        }
    }
    return $max
}

function Bump-Version {
    param([string]$Current, [string]$BumpType)
    $nums = Parse-Version $Current
    switch ($BumpType) {
        'major' { $nums[0]++; $nums[1]=0; $nums[2]=0; $nums[3]=0 }
        'minor' { $nums[1]++; $nums[2]=0; $nums[3]=0 }
        'patch' { $nums[2]++; $nums[3]=0 }
        'micro' { $nums[3]++ }
        default { throw "Unknown bump type '$BumpType'" }
    }
    return ($nums -join '.')
}
