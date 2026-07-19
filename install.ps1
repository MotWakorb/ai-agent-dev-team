#Requires -Version 5.0
<#
.SYNOPSIS
    Claude Agent Dev Team — Claude Code + Codex PowerShell Installer
.DESCRIPTION
    Symlinks skills into ~/.claude/skills/ and ~/.agents/skills/ so git pull updates automatically.
    Use -Copy to copy instead of symlink (for customization).
.PARAMETER Copy
    Copy skills instead of symlink (for customization without affecting the repo)
.EXAMPLE
    ./install.ps1              # Symlink (default)
    ./install.ps1 -Copy        # Copy instead
#>

[CmdletBinding()]
param(
    [switch]$Copy
)

$ErrorActionPreference = 'Stop'

$RepoDir = $PSScriptRoot
$ClaudeSkillsDir = Join-Path (Join-Path $HOME '.claude') 'skills'
$CodexSkillsDir = Join-Path (Join-Path $HOME '.agents') 'skills'
$SkillDestinations = @($ClaudeSkillsDir, $CodexSkillsDir)
$RetroDir = Join-Path $HOME 'retros'

$Skills = @(
    '_shared'
    'security-engineer'
    'it-architect'
    'project-manager'
    'project-engineer'
    'ux-designer'
    'code-reviewer'
    'database-engineer'
    'sre'
    'qa-engineer'
    'technical-writer'
    'retro'
    'retro-sync'
    'retro-mine'
    'team-plan'
    'team-review'
    'standup'
    'grooming'
    'spike'
    'postmortem'
    'onboard'
    'release-check'
)

function Test-Symlink {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $false }
    $item = Get-Item $Path -Force
    return [bool]($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)
}

function Get-SymlinkTarget {
    param([string]$Path)
    # PS5 doesn't have .Target — use fsutil on Windows, readlink on Unix
    if ($IsWindows -or (-not (Test-Path variable:IsWindows) -and $env:OS -eq 'Windows_NT')) {
        $output = cmd /c "dir `"$(Split-Path $Path)`"" 2>&1 | Where-Object { $_ -match [regex]::Escape((Split-Path $Path -Leaf)) -and $_ -match '\[(.+)\]' }
        if ($output -and $Matches[1]) { return $Matches[1] }
        return $null
    }
    else {
        try { return (readlink $Path) } catch { return $null }
    }
}

if ($Copy) { $Mode = 'copy' } else { $Mode = 'symlink' }

Write-Host 'Installing Claude Agent Dev Team skills for Claude Code and Codex...'
Write-Host "  Mode: $Mode"
Write-Host "  From: $RepoDir"
Write-Host "  Claude: $ClaudeSkillsDir"
Write-Host "  Codex:  $CodexSkillsDir"
Write-Host ''

# Create directories
foreach ($destination in $SkillDestinations) {
    if (-not (Test-Path $destination)) { New-Item -ItemType Directory -Path $destination -Force | Out-Null }
}
if (-not (Test-Path $RetroDir)) { New-Item -ItemType Directory -Path $RetroDir -Force | Out-Null }

$installed = 0
$skipped = 0
$updated = 0

foreach ($SkillsDir in $SkillDestinations) {
  foreach ($skill in $Skills) {
    $source = Join-Path $RepoDir $skill
    $target = Join-Path $SkillsDir $skill

    if (-not (Test-Path $source)) {
        Write-Host "  WARN: $skill not found in repo, skipping"
        $skipped++
        continue
    }

    if (Test-Path $target) {
        if (Test-Symlink $target) {
            $existing = Get-SymlinkTarget $target
            if ($existing -eq $source) {
                Write-Host "  OK:   $skill (already linked)"
                $skipped++
                continue
            }
            else {
                Write-Host "  UPDATE: $skill (repointing symlink)"
                Remove-Item $target -Force
                $updated++
            }
        }
        else {
            if ($Mode -eq 'symlink') {
                Write-Host "  SKIP: $skill (directory exists - use -Copy to overwrite, or remove manually)"
                $skipped++
                continue
            }
            else {
                Write-Host "  UPDATE: $skill (overwriting)"
                Remove-Item $target -Recurse -Force
                $updated++
            }
        }
    }

    if ($Mode -eq 'symlink') {
        New-Item -ItemType SymbolicLink -Path $target -Target $source | Out-Null
        Write-Host "  LINK: $skill"
    }
    else {
        Copy-Item -Path $source -Destination $target -Recurse
        Write-Host "  COPY: $skill"
    }
    $installed++
  }
}

# --- Manage ~/.claude/CLAUDE.md orchestration block ---
$ClaudeMd = Join-Path (Join-Path $HOME '.claude') 'CLAUDE.md'
$MarkerStart = '# --- Claude Agent Dev Team (managed) ---'
$MarkerEnd = '# --- End Claude Agent Dev Team ---'

$Block = @"
$MarkerStart
# Orchestration discipline - read before spawning agents or doing implementation work.
# This file is managed by install.ps1. To update, re-run the installer.
Read ~/.claude/skills/_shared/orchestration.md before spawning any agent or doing any implementation work.
$MarkerEnd
"@

if ((Test-Path $ClaudeMd) -and (Get-Content $ClaudeMd -Raw) -match [regex]::Escape($MarkerStart)) {
    # Replace existing managed block (idempotent update)
    $content = Get-Content $ClaudeMd -Raw
    $pattern = [regex]::Escape($MarkerStart) + '[\s\S]*?' + [regex]::Escape($MarkerEnd)
    $content = [regex]::Replace($content, $pattern, $Block)
    Set-Content -Path $ClaudeMd -Value $content -NoNewline
    Write-Host "  CLAUDE.md: updated managed block"
}
else {
    # Append managed block
    if ((Test-Path $ClaudeMd) -and (Get-Content $ClaudeMd -Raw).Length -gt 0) {
        Add-Content -Path $ClaudeMd -Value "`n"
    }
    # Ensure parent directory exists
    $claudeDir = Split-Path $ClaudeMd
    if (-not (Test-Path $claudeDir)) { New-Item -ItemType Directory -Path $claudeDir -Force | Out-Null }
    Add-Content -Path $ClaudeMd -Value $Block
    Write-Host "  CLAUDE.md: added orchestration block to $ClaudeMd"
}

# --- Manage ~/.codex/AGENTS.md orchestration block ---
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
$AgentsMd = Join-Path $CodexHome 'AGENTS.md'
$CodexBlock = @"
$MarkerStart
# Orchestration discipline - read before spawning agents or doing implementation work.
# This file is managed by install.ps1. To update, re-run the installer.
Read ~/.agents/skills/_shared/orchestration.md before spawning any agent or doing any implementation work.
$MarkerEnd
"@

if ((Test-Path $AgentsMd) -and (Get-Content $AgentsMd -Raw) -match [regex]::Escape($MarkerStart)) {
    $content = Get-Content $AgentsMd -Raw
    $pattern = [regex]::Escape($MarkerStart) + '[\s\S]*?' + [regex]::Escape($MarkerEnd)
    $content = [regex]::Replace($content, $pattern, $CodexBlock)
    Set-Content -Path $AgentsMd -Value $content -NoNewline
    Write-Host "  AGENTS.md: updated managed block"
}
else {
    if ((Test-Path $AgentsMd) -and (Get-Content $AgentsMd -Raw).Length -gt 0) {
        Add-Content -Path $AgentsMd -Value "`n"
    }
    if (-not (Test-Path $CodexHome)) { New-Item -ItemType Directory -Path $CodexHome -Force | Out-Null }
    Add-Content -Path $AgentsMd -Value $CodexBlock
    Write-Host "  AGENTS.md: added orchestration block to $AgentsMd"
}

Write-Host ''
Write-Host 'Done!'
Write-Host "  Installed: $installed"
Write-Host "  Updated:   $updated"
Write-Host "  Skipped:   $skipped"
Write-Host "  Retro dir: $RetroDir"
Write-Host ''

if ($Mode -eq 'symlink') {
    Write-Host "Skills are symlinked - run 'git pull' in this repo to update them."
    Write-Host 'To customize a skill without affecting the repo, copy it manually:'
    Write-Host "  Copy-Item -Recurse $ClaudeSkillsDir\<skill> $ClaudeSkillsDir\<skill>-custom"
    Write-Host ''
    Write-Host 'NOTE: On Windows, creating symlinks may require running as Administrator'
    Write-Host 'or enabling Developer Mode (Settings > Update & Security > For developers).'
}
else {
    Write-Host "Skills are copied - changes to the repo won't auto-update."
    Write-Host "Run './install.ps1 -Copy' again after 'git pull' to update."
}
