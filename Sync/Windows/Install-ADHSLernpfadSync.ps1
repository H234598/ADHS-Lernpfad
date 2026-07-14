[CmdletBinding()]
param(
    [string]$Target = "$env:USERPROFILE\Documents\Obsidian\ADHS-Lernpfad",
    [ValidateSet('safe-pull', 'prompt-pull', 'forced-pull', 'additive-pull', 'full-sync')]
    [string]$Mode = 'safe-pull',
    [string]$DeviceBranch = '',
    [string]$BaseBranch = 'main',
    [string]$RepoUrl = 'https://github.com/H234598/ADHS-Lernpfad.git',
    [ValidateRange(1, 1440)]
    [int]$IntervalMinutes = 30,
    [switch]$Manual,
    [switch]$AdoptExistingTarget
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($Mode -eq 'full-sync' -and [string]::IsNullOrWhiteSpace($DeviceBranch)) {
    throw 'full-sync benötigt -DeviceBranch, z. B. sync/mein-windows-pc'
}
if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) {
    throw 'Git für Windows fehlt oder ist nicht im PATH.'
}
if (-not (Get-Command robocopy.exe -ErrorAction SilentlyContinue)) {
    throw 'Robocopy fehlt; es ist Bestandteil unterstützter Windows-Versionen.'
}

$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallRoot = Join-Path $env:LOCALAPPDATA 'ADHS-Lernpfad-Sync'
$EnginePath = Join-Path $InstallRoot 'Sync-ADHSLernpfad.ps1'
$ConfigPath = Join-Path $InstallRoot 'config.json'
$RepoDir = Join-Path $InstallRoot 'repo'
$TaskName = 'ADHS-Lernpfad Sync'

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
Copy-Item -LiteralPath (Join-Path $SourceDir 'Sync-ADHSLernpfad.ps1') -Destination $EnginePath -Force

$config = [ordered]@{
    RepoUrl = $RepoUrl
    Remote = 'origin'
    BaseBranch = $BaseBranch
    RepoDir = $RepoDir
    TargetDir = $Target
    Mode = $Mode
    DeviceBranch = $DeviceBranch
    ProtectObsidian = $true
    AdoptExistingTarget = [bool]$AdoptExistingTarget
    DiscardPending = $false
    GitAuthorName = 'ADHS Sync'
    GitAuthorEmail = 'adhs-sync@localhost'
}
$config | ConvertTo-Json | Set-Content -LiteralPath $ConfigPath -Encoding UTF8

if (-not $Manual) {
    $powerShellCommand = Get-Command pwsh.exe -ErrorAction SilentlyContinue
    if ($null -eq $powerShellCommand) {
        $powerShellCommand = Get-Command powershell.exe -ErrorAction Stop
    }
    $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$EnginePath`" -Config `"$ConfigPath`" -NonInteractive"
    $action = New-ScheduledTaskAction -Execute $powerShellCommand.Source -Argument $arguments
    $repeating = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
        -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
        -RepetitionDuration (New-TimeSpan -Days 3650)
    $atLogon = New-ScheduledTaskTrigger -AtLogOn
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Hours 1)
    Register-ScheduledTask -TaskName $TaskName -Action $action `
        -Trigger @($repeating, $atLogon) -Settings $settings `
        -Description 'Synchronisiert den ADHS-Lernpfad mit einem Obsidian-Vault.' `
        -Force | Out-Null
}

& $EnginePath -Config $ConfigPath
if ($LASTEXITCODE -ne 0) {
    throw "Erster Synchronisationslauf ist mit Code $LASTEXITCODE fehlgeschlagen."
}

Write-Host "Installiert: $EnginePath"
Write-Host "Konfiguration: $ConfigPath"
Write-Host "Ziel: $Target"
Write-Host "Modus: $Mode"
Write-Host "Aufgabenplanung: $(-not $Manual)"
