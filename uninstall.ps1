#Requires -Version 5.0
<#
.SYNOPSIS
    AI Agent Dev Team — Claude Code + Codex PowerShell Uninstaller
.DESCRIPTION
    Removes skills installed by install.ps1 from Claude Code and Codex.
.PARAMETER Yes
    Skip confirmation prompt
.EXAMPLE
    ./uninstall.ps1        # Prompt before removing
    ./uninstall.ps1 -Yes   # Remove without prompting
#>

[CmdletBinding()]
param(
    [switch]$Yes
)

$ErrorActionPreference = 'Stop'

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

# Check if anything is installed
$found = 0
foreach ($SkillsDir in $SkillDestinations) {
    foreach ($skill in $Skills) {
        $target = Join-Path $SkillsDir $skill
        if (Test-Path $target) { $found++ }
    }
}

if ($found -eq 0) {
    Write-Host "Nothing to uninstall - no AI Agent Dev Team skills found in $SkillsDir"
    return
}

Write-Host "Found $found installed skill(s) in $SkillsDir"
Write-Host ''

if (-not $Yes) {
    $confirm = Read-Host 'Remove all AI Agent Dev Team skills? [y/N]'
    if ($confirm -notmatch '^[Yy]$') {
        Write-Host 'Aborted.'
        return
    }
}

Write-Host ''
Write-Host 'Uninstalling AI Agent Dev Team skills from Claude Code and Codex...'
$removed = 0
foreach ($SkillsDir in $SkillDestinations) {
    foreach ($skill in $Skills) {
        $target = Join-Path $SkillsDir $skill
        if (Test-Path $target) {
            Remove-Item $target -Recurse -Force
            Write-Host "  Removed: $target"
            $removed++
        }
    }
}

# --- Remove managed block from ~/.claude/CLAUDE.md ---
$ClaudeMd = Join-Path (Join-Path $HOME '.claude') 'CLAUDE.md'
$MarkerStart = '# --- AI Agent Dev Team (managed) ---'
$MarkerEnd = '# --- End AI Agent Dev Team ---'
$LegacyMarkerStart = '# --- Claude Agent Dev Team (managed) ---'
$LegacyMarkerEnd = '# --- End Claude Agent Dev Team ---'

if (Test-Path $ClaudeMd) {
    $content = (Get-Content $ClaudeMd -Raw).Replace($LegacyMarkerStart, $MarkerStart).Replace($LegacyMarkerEnd, $MarkerEnd)
    Set-Content -Path $ClaudeMd -Value $content -NoNewline
}
if ((Test-Path $ClaudeMd) -and (Get-Content $ClaudeMd -Raw) -match [regex]::Escape($MarkerStart)) {
    $content = Get-Content $ClaudeMd -Raw
    $pattern = [regex]::Escape($MarkerStart) + '[\s\S]*?' + [regex]::Escape($MarkerEnd)
    $content = [regex]::Replace($content, $pattern, '').Trim()
    if ($content.Length -eq 0) {
        Remove-Item $ClaudeMd -Force
        Write-Host "  Removed: $ClaudeMd (was empty after cleanup)"
    }
    else {
        Set-Content -Path $ClaudeMd -Value $content -NoNewline
        Write-Host "  Cleaned: $ClaudeMd (removed managed block, preserved other content)"
    }
}

# --- Remove managed block from ~/.codex/AGENTS.md ---
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
$AgentsMd = Join-Path $CodexHome 'AGENTS.md'
if (Test-Path $AgentsMd) {
    $content = (Get-Content $AgentsMd -Raw).Replace($LegacyMarkerStart, $MarkerStart).Replace($LegacyMarkerEnd, $MarkerEnd)
    Set-Content -Path $AgentsMd -Value $content -NoNewline
}
if ((Test-Path $AgentsMd) -and (Get-Content $AgentsMd -Raw) -match [regex]::Escape($MarkerStart)) {
    $content = Get-Content $AgentsMd -Raw
    $pattern = [regex]::Escape($MarkerStart) + '[\s\S]*?' + [regex]::Escape($MarkerEnd)
    $content = [regex]::Replace($content, $pattern, '').Trim()
    if ($content.Length -eq 0) {
        Remove-Item $AgentsMd -Force
        Write-Host "  Removed: $AgentsMd (was empty after cleanup)"
    }
    else {
        Set-Content -Path $AgentsMd -Value $content -NoNewline
        Write-Host "  Cleaned: $AgentsMd (removed managed block, preserved other content)"
    }
}

# --- Remove Codex PreToolUse enforcement hook ---
$CodexHooksJson = Join-Path $CodexHome 'hooks.json'
if ((Test-Path $CodexHooksJson) -and (Get-Content $CodexHooksJson -Raw) -match 'pretooluse\.py') {
    $CodexHooks = Get-Content $CodexHooksJson -Raw | ConvertFrom-Json
    $remaining = @($CodexHooks.hooks.PreToolUse | Where-Object {
        ($_ | ConvertTo-Json -Depth 10) -notmatch 'pretooluse\.py'
    })
    if ($remaining.Count -eq 0) {
        $CodexHooks.hooks.PSObject.Properties.Remove('PreToolUse')
    }
    else {
        $CodexHooks.hooks.PreToolUse = $remaining
    }
    if ($CodexHooks.hooks.PSObject.Properties.Count -eq 0) {
        $CodexHooks.PSObject.Properties.Remove('hooks')
    }
    $CodexHooks | ConvertTo-Json -Depth 10 | Set-Content $CodexHooksJson
    Write-Host "  Cleaned: Codex PreToolUse hook removed from $CodexHooksJson"
}

Write-Host ''
Write-Host "Done. Removed $removed skill installation(s)."
Write-Host "Note: $RetroDir was not removed (may contain your retrospectives)"
