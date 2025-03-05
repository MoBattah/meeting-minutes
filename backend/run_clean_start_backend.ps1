# PowerShell script to run clean_start_backend.cmd
param(
    [string]$ModelName = ""
)

Write-Host "Running clean_start_backend.cmd using PowerShell wrapper..."
if ($ModelName -eq "") {
    cmd.exe /c "$PSScriptRoot\clean_start_backend.cmd"
} else {
    cmd.exe /c "$PSScriptRoot\clean_start_backend.cmd $ModelName"
}
