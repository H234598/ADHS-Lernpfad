[CmdletBinding()]
param(
    [switch]$PurgeConfig,
    [switch]$RemoveCheckout
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$InstallRoot = Join-Path $env:LOCALAPPDATA 'ADHS-Lernpfad-Sync'
$TaskName = 'ADHS-Lernpfad Sync'

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Remove-Item -LiteralPath (Join-Path $InstallRoot 'Sync-ADHSLernpfad.ps1') -Force -ErrorAction SilentlyContinue
if ($PurgeConfig) {
    Remove-Item -LiteralPath (Join-Path $InstallRoot 'config.json') -Force -ErrorAction SilentlyContinue
}
if ($RemoveCheckout) {
    Remove-Item -LiteralPath (Join-Path $InstallRoot 'repo') -Recurse -Force -ErrorAction SilentlyContinue
}

if (Test-Path -LiteralPath $InstallRoot) {
    $remaining = Get-ChildItem -LiteralPath $InstallRoot -Force -ErrorAction SilentlyContinue
    if ($null -eq $remaining -or $remaining.Count -eq 0) {
        Remove-Item -LiteralPath $InstallRoot -Force
    }
}

Write-Host 'Windows-Sync entfernt. Der Obsidian-Vault blieb unverändert.'
