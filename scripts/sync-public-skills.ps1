[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SourceRoot,

    [switch]$Check,
    [switch]$Apply,
    [switch]$Publish,
    [string]$Message = "Sync public architectural review skills",
    [string]$PythonExecutable = $env:KANGMAOJIAN_SYNC_PYTHON,
    [string]$GitExecutable = $env:GIT_EXE,
    [string]$GhExecutable = $env:GH_EXE
)

$ErrorActionPreference = "Stop"

if ($Check -and $Apply) {
    throw "Choose either -Check or -Apply."
}
if ($Publish -and -not $Apply) {
    throw "-Publish requires -Apply."
}
if (-not $Check -and -not $Apply) {
    $Check = $true
}

if (-not $PythonExecutable) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python was not found. Set KANGMAOJIAN_SYNC_PYTHON or pass -PythonExecutable."
    }
    $PythonExecutable = $pythonCommand.Source
}

$engine = Join-Path $PSScriptRoot "sync_public_skills.py"
$engineArguments = @($engine, "--source-root", $SourceRoot)
if ($Apply) {
    $engineArguments += "--apply"
} else {
    $engineArguments += "--check"
}
if ($Publish) {
    if (-not $GitExecutable) {
        $gitCommand = Get-Command git -ErrorAction SilentlyContinue
        if (-not $gitCommand) {
            throw "Git was not found. Set GIT_EXE or pass -GitExecutable."
        }
        $GitExecutable = $gitCommand.Source
    }
    if (-not $GhExecutable) {
        $ghCommand = Get-Command gh -ErrorAction SilentlyContinue
        if (-not $ghCommand) {
            throw "GitHub CLI was not found. Set GH_EXE or pass -GhExecutable."
        }
        $GhExecutable = $ghCommand.Source
    }
    $engineArguments += @(
        "--publish",
        "--message", $Message,
        "--git-executable", $GitExecutable,
        "--gh-executable", $GhExecutable
    )
}

& $PythonExecutable -B @engineArguments
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
