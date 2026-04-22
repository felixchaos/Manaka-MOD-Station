param(
    [Parameter(Mandatory = $true)]
    [string]$Executable,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)

$rootDir = Join-Path $env:LOCALAPPDATA "ManakaModStation\dev-runner"
$stateFile = Join-Path $rootDir "current.pid"
New-Item -ItemType Directory -Path $rootDir -Force | Out-Null

if (Test-Path $stateFile) {
    $previousPid = Get-Content $stateFile -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($previousPid -and $previousPid -match '^\d+$') {
        $previousProcess = Get-Process -Id ([int]$previousPid) -ErrorAction SilentlyContinue
        if ($null -ne $previousProcess) {
            Stop-Process -Id $previousProcess.Id -Force -ErrorAction SilentlyContinue
            Wait-Process -Id $previousProcess.Id -ErrorAction SilentlyContinue
        }
    }
    Remove-Item $stateFile -Force -ErrorAction SilentlyContinue
}

$runDir = Join-Path $rootDir ([Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $runDir -Force | Out-Null

$targetExe = Join-Path $runDir ([System.IO.Path]::GetFileName($Executable))
Copy-Item -Path $Executable -Destination $targetExe -Force

$arguments = @($RemainingArgs | Where-Object { $_ -and $_.Trim().Length -gt 0 })
if ($arguments.Count -gt 0) {
    $process = Start-Process -FilePath $targetExe -ArgumentList $arguments -PassThru
} else {
    $process = Start-Process -FilePath $targetExe -PassThru
}
$process.Id | Set-Content -Path $stateFile -NoNewline
$process | Wait-Process
if ((Test-Path $stateFile) -and ((Get-Content $stateFile -ErrorAction SilentlyContinue | Select-Object -First 1) -eq [string]$process.Id)) {
    Remove-Item $stateFile -Force -ErrorAction SilentlyContinue
}
exit $process.ExitCode