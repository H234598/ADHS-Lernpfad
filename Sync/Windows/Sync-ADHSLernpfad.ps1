[CmdletBinding()]
param(
    [string]$Config = "$env:LOCALAPPDATA\ADHS-Lernpfad-Sync\config.json",
    [switch]$NonInteractive
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Log {
    param([string]$Message)
    Write-Host "[$(Get-Date -Format o)] $Message"
}

function Stop-Sync {
    param([int]$Code, [string]$Message)
    Write-Error $Message
    exit $Code
}

if (-not (Test-Path -LiteralPath $Config -PathType Leaf)) {
    Stop-Sync 66 "Konfigurationsdatei fehlt: $Config"
}
$cfg = Get-Content -LiteralPath $Config -Raw -Encoding UTF8 | ConvertFrom-Json

function Get-ConfigValue {
    param([string]$Name, $Default)
    $property = $cfg.PSObject.Properties[$Name]
    if ($null -ne $property -and $null -ne $property.Value -and "$($property.Value)" -ne '') {
        return $property.Value
    }
    return $Default
}

$RepoUrl = [string](Get-ConfigValue 'RepoUrl' 'https://github.com/H234598/ADHS-Lernpfad.git')
$Remote = [string](Get-ConfigValue 'Remote' 'origin')
$BaseBranch = [string](Get-ConfigValue 'BaseBranch' 'main')
$RepoDir = [string](Get-ConfigValue 'RepoDir' "$env:LOCALAPPDATA\ADHS-Lernpfad-Sync\repo")
$TargetDir = [string](Get-ConfigValue 'TargetDir' "$env:USERPROFILE\Documents\Obsidian\ADHS-Lernpfad")
$Mode = [string](Get-ConfigValue 'Mode' 'safe-pull')
$DeviceBranch = [string](Get-ConfigValue 'DeviceBranch' '')
$ProtectObsidian = [bool](Get-ConfigValue 'ProtectObsidian' $true)
$AdoptExistingTarget = [bool](Get-ConfigValue 'AdoptExistingTarget' $false)
$DiscardPending = [bool](Get-ConfigValue 'DiscardPending' $false)
$GitAuthorName = [string](Get-ConfigValue 'GitAuthorName' 'ADHS Sync')
$GitAuthorEmail = [string](Get-ConfigValue 'GitAuthorEmail' 'adhs-sync@localhost')
$StateFile = Join-Path $RepoDir '.git\adhs-sync-state.json'

$AllowedModes = @('safe-pull', 'prompt-pull', 'forced-pull', 'additive-pull', 'full-sync')
if ($AllowedModes -notcontains $Mode) { Stop-Sync 64 "Unbekannter Modus: $Mode" }
if ($Mode -eq 'full-sync') {
    if ([string]::IsNullOrWhiteSpace($DeviceBranch)) { Stop-Sync 64 'full-sync benötigt DeviceBranch' }
    if ($DeviceBranch -eq $BaseBranch) { Stop-Sync 64 'DeviceBranch darf nicht BaseBranch entsprechen' }
}

foreach ($command in @('git.exe', 'robocopy.exe')) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        Stop-Sync 127 "Benötigtes Programm fehlt: $command"
    }
}

$ProtectedDirectories = @('.git', '.trash')
if ($ProtectObsidian) { $ProtectedDirectories += '.obsidian' }
$ProtectedFiles = @('.stfolder', '.stignore', '.nomedia', '.DS_Store', 'Thumbs.db', 'desktop.ini')

function Invoke-Git {
    param(
        [string[]]$Arguments,
        [switch]$AllowFailure,
        [switch]$Capture
    )
    $output = & git.exe -C $RepoDir @Arguments 2>&1
    $code = $LASTEXITCODE
    if ($code -ne 0 -and -not $AllowFailure) {
        throw "git $($Arguments -join ' ') fehlgeschlagen ($code): $($output -join [Environment]::NewLine)"
    }
    if ($Capture) { return ($output -join "`n").Trim() }
    return $code
}

function Test-GitSuccess {
    param([string[]]$Arguments)
    & git.exe -C $RepoDir @Arguments *> $null
    return ($LASTEXITCODE -eq 0)
}

function Ensure-Checkout {
    $parent = Split-Path -Parent $RepoDir
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $TargetDir) | Out-Null
    if ((Test-Path -LiteralPath $RepoDir) -and -not (Test-Path -LiteralPath (Join-Path $RepoDir '.git'))) {
        Stop-Sync 65 "Privater Checkoutpfad ist kein Git-Repository: $RepoDir"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $RepoDir '.git'))) {
        & git.exe clone --branch $BaseBranch --single-branch $RepoUrl $RepoDir
        if ($LASTEXITCODE -ne 0) { Stop-Sync $LASTEXITCODE 'Git-Clone fehlgeschlagen' }
    }
    if (-not (Test-GitSuccess @('remote', 'get-url', $Remote))) {
        Invoke-Git @('remote', 'add', $Remote, $RepoUrl) | Out-Null
    }
    Invoke-Git @('remote', 'set-url', $Remote, $RepoUrl) | Out-Null
    Invoke-Git @('config', 'user.name', $GitAuthorName) | Out-Null
    Invoke-Git @('config', 'user.email', $GitAuthorEmail) | Out-Null
}

function Get-RelativePath {
    param([string]$Root, [string]$FullName)
    $prefix = $Root.TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
    return $FullName.Substring($prefix.Length).Replace('\', '/')
}

function Test-ProtectedRelativePath {
    param([string]$RelativePath)
    $parts = $RelativePath -split '/'
    foreach ($part in $parts) {
        if ($ProtectedDirectories -contains $part) { return $true }
    }
    return ($ProtectedFiles -contains $parts[-1])
}

function Get-TreeManifest {
    param([string]$Root)
    $manifest = @{}
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) { return $manifest }
    Get-ChildItem -LiteralPath $Root -File -Recurse -Force | ForEach-Object {
        $relative = Get-RelativePath $Root $_.FullName
        if (-not (Test-ProtectedRelativePath $relative)) {
            $manifest[$relative] = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
        }
    }
    return $manifest
}

function Test-TreeDifferent {
    param([string]$Source, [string]$Destination)
    $sourceManifest = Get-TreeManifest $Source
    $destinationManifest = Get-TreeManifest $Destination
    if ($sourceManifest.Count -ne $destinationManifest.Count) { return $true }
    foreach ($key in $sourceManifest.Keys) {
        if (-not $destinationManifest.ContainsKey($key)) { return $true }
        if ($sourceManifest[$key] -ne $destinationManifest[$key]) { return $true }
    }
    return $false
}

function Invoke-RobocopySync {
    param([string]$Source, [string]$Destination, [ValidateSet('mirror', 'additive')] [string]$CopyMode)
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    $arguments = @($Source, $Destination)
    if ($CopyMode -eq 'mirror') {
        $arguments += '/MIR'
    } else {
        $arguments += @('/E', '/XC', '/XN', '/XO')
    }
    $arguments += @('/R:2', '/W:1', '/NFL', '/NDL', '/NJH', '/NJS', '/NP')
    if ($ProtectedDirectories.Count -gt 0) { $arguments += '/XD'; $arguments += $ProtectedDirectories }
    if ($ProtectedFiles.Count -gt 0) { $arguments += '/XF'; $arguments += $ProtectedFiles }
    & robocopy.exe @arguments | Out-Null
    $code = $LASTEXITCODE
    if ($code -ge 8) { Stop-Sync $code "Robocopy fehlgeschlagen: $Source -> $Destination" }
}

function Confirm-Overwrite {
    param([string]$Reason)
    if ($NonInteractive) { Stop-Sync 4 "Interaktive Bestätigung nicht möglich: $Reason" }
    $answer = Read-Host "$Reason Lokale Abweichungen verwerfen? [y/N]"
    if ($answer -notmatch '^[Yy]$') { Stop-Sync 4 'Abgebrochen; lokale Dateien bleiben erhalten' }
}

function Get-CurrentBranch {
    return [string](Invoke-Git @('symbolic-ref', '--quiet', '--short', 'HEAD') -AllowFailure -Capture)
}

function Get-PendingCommitCount {
    $upstream = [string](Invoke-Git @('rev-parse', '--abbrev-ref', '@{upstream}') -AllowFailure -Capture)
    if ([string]::IsNullOrWhiteSpace($upstream)) { return 0 }
    return [int](Invoke-Git @('rev-list', '--count', "$upstream..HEAD") -Capture)
}

function Write-State {
    $state = [ordered]@{
        mode = $Mode
        branch = Get-CurrentBranch
        commit = Invoke-Git @('rev-parse', 'HEAD') -Capture
        target = $TargetDir
        updated_at = (Get-Date).ToString('o')
    }
    $state | ConvertTo-Json | Set-Content -LiteralPath $StateFile -Encoding UTF8
}

function Run-PullMode {
    $pending = Get-PendingCommitCount
    if ($pending -gt 0 -and -not ($Mode -eq 'forced-pull' -and $DiscardPending)) {
        Stop-Sync 9 "$pending nicht gepushte Commit(s) im privaten Checkout"
    }

    $targetChanged = $false
    if ($Mode -ne 'additive-pull' -and (Test-TreeDifferent $RepoDir $TargetDir)) {
        $targetChanged = $true
        Write-Log 'Lokale Abweichungen im Vault wurden erkannt.'
    }
    if ($Mode -eq 'safe-pull' -and $targetChanged) { Stop-Sync 4 'safe-pull bricht ab und überschreibt nichts' }
    if ($Mode -eq 'prompt-pull' -and $targetChanged) { Confirm-Overwrite 'Der Vault weicht vom letzten Spiegelstand ab.' }

    Invoke-Git @('reset', '--hard') | Out-Null
    Invoke-Git @('clean', '-fd') | Out-Null
    Invoke-Git @('fetch', '--prune', $Remote, $BaseBranch) | Out-Null
    Invoke-Git @('checkout', '-f', '-B', $BaseBranch, "$Remote/$BaseBranch") | Out-Null
    Invoke-RobocopySync $RepoDir $TargetDir ($(if ($Mode -eq 'additive-pull') { 'additive' } else { 'mirror' }))
    Write-State
    Write-Log "Synchronisierung abgeschlossen: Modus=$Mode Branch=$BaseBranch Ziel=$TargetDir"
}

function Test-RemoteDeviceBranch {
    & git.exe -C $RepoDir ls-remote --exit-code --heads $Remote $DeviceBranch *> $null
    return ($LASTEXITCODE -eq 0)
}

function Prepare-DeviceBranch {
    param([bool]$RemoteExists)
    if (Test-GitSuccess @('show-ref', '--verify', '--quiet', "refs/heads/$DeviceBranch")) {
        Invoke-Git @('checkout', $DeviceBranch) | Out-Null
    } elseif ($RemoteExists) {
        Invoke-Git @('checkout', '-b', $DeviceBranch, '--track', "$Remote/$DeviceBranch") | Out-Null
    } else {
        Invoke-Git @('checkout', '-b', $DeviceBranch, "$Remote/$BaseBranch") | Out-Null
    }
}

function Push-DeviceBranch {
    & git.exe -C $RepoDir push -u $Remote "HEAD:refs/heads/$DeviceBranch"
    if ($LASTEXITCODE -ne 0) { Stop-Sync 8 "Push nach $DeviceBranch fehlgeschlagen; Commit bleibt lokal erhalten" }
}

function Run-FullSync {
    Invoke-Git @('reset', '--hard') | Out-Null
    Invoke-Git @('clean', '-fd') | Out-Null
    Invoke-Git @('fetch', '--prune', $Remote, $BaseBranch) | Out-Null
    $remoteExists = Test-RemoteDeviceBranch
    if ($remoteExists) {
        Invoke-Git @('fetch', $Remote, "$DeviceBranch`:refs/remotes/$Remote/$DeviceBranch") | Out-Null
    }
    Prepare-DeviceBranch $remoteExists

    $targetChanged = Test-TreeDifferent $RepoDir $TargetDir
    if (-not (Test-Path -LiteralPath $StateFile) -and $targetChanged -and -not $AdoptExistingTarget) {
        Stop-Sync 6 'Vorhandener Vault weicht beim ersten Full Sync ab; AdoptExistingTarget bewusst aktivieren'
    }

    $ahead = 0
    $behind = 0
    if ($remoteExists) {
        $ahead = [int](Invoke-Git @('rev-list', '--count', "$Remote/$DeviceBranch..HEAD") -Capture)
        $behind = [int](Invoke-Git @('rev-list', '--count', "HEAD..$Remote/$DeviceBranch") -Capture)
    }
    if ($ahead -gt 0 -and $behind -gt 0) { Stop-Sync 7 'Privater Checkout und Remote-Gerätebranch sind divergiert' }
    if ($targetChanged -and $behind -gt 0) { Stop-Sync 7 'Vault und Remote-Gerätebranch wurden beide geändert' }

    if (-not $targetChanged -and $behind -gt 0) {
        Invoke-Git @('merge', '--ff-only', "$Remote/$DeviceBranch") | Out-Null
        Invoke-RobocopySync $RepoDir $TargetDir 'mirror'
        Write-State
        Write-Log "Remote-Gerätebranch übernommen: $DeviceBranch"
        return
    }

    if ($targetChanged) {
        Invoke-RobocopySync $TargetDir $RepoDir 'mirror'
        Invoke-Git @('add', '-A') | Out-Null
        & git.exe -C $RepoDir diff --cached --quiet
        if ($LASTEXITCODE -ne 0) {
            Invoke-Git @('commit', '-m', "Sync from Windows device $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')") | Out-Null
        }
    }

    if ($remoteExists) {
        $ahead = [int](Invoke-Git @('rev-list', '--count', "$Remote/$DeviceBranch..HEAD") -Capture)
    } else {
        $ahead = 1
    }
    if (-not $remoteExists -or $ahead -gt 0) { Push-DeviceBranch }

    Invoke-RobocopySync $RepoDir $TargetDir 'mirror'
    Write-State
    Write-Log "Full Sync abgeschlossen: Gerätebranch=$DeviceBranch Ziel=$TargetDir"
}

Ensure-Checkout
$mutexBytes = [Text.Encoding]::UTF8.GetBytes($TargetDir.ToLowerInvariant())
$sha = [Security.Cryptography.SHA256]::Create()
$mutexHash = ([BitConverter]::ToString($sha.ComputeHash($mutexBytes))).Replace('-', '').Substring(0, 20)
$mutex = New-Object Threading.Mutex($false, "Local\ADHSLernpfadSync-$mutexHash")
if (-not $mutex.WaitOne(0)) {
    Write-Log 'Ein anderer Synchronisationslauf ist bereits aktiv.'
    exit 0
}
try {
    if ($Mode -eq 'full-sync') { Run-FullSync } else { Run-PullMode }
} finally {
    $mutex.ReleaseMutex() | Out-Null
    $mutex.Dispose()
    $sha.Dispose()
}
