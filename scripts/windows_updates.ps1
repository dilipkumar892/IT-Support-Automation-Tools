<#
.SYNOPSIS
    Queries Windows Update status, hotfixes, and update service health.
.DESCRIPTION
    Checks wuauserv and bits services, retrieves recently installed KBs/Hotfixes,
    and returns structured diagnostic output.
.EXAMPLE
    .\windows_updates.ps1 -AsJson
#>

[CmdletBinding()]
param (
    [switch]$AsJson = $true,
    [int]$RecentLimit = 10
)

$ErrorActionPreference = "SilentlyContinue"

# Check Windows Update services
$Services = @("wuauserv", "bits", "cryptsvc", "trustedinstaller") | ForEach-Object {
    $svc = Get-Service -Name $_ 2>$null
    if ($svc) {
        [PSCustomObject]@{
            ServiceName = $_
            DisplayName = $svc.DisplayName
            Status      = $svc.Status.ToString()
            StartType   = $svc.StartType.ToString()
        }
    } else {
        [PSCustomObject]@{
            ServiceName = $_
            DisplayName = $_
            Status      = "NotFound"
            StartType   = "Unknown"
        }
    }
}

# Installed Hotfixes
$Hotfixes = Get-HotFix 2>$null | Sort-Object -Property InstalledOn -Descending | Select-Object -First $RecentLimit | ForEach-Object {
    [PSCustomObject]@{
        HotFixID    = $_.HotFixID
        Description = $_.Description
        InstalledOn = if ($_.InstalledOn) { $_.InstalledOn.ToString("yyyy-MM-dd") } else { "Unknown" }
        InstalledBy = $_.InstalledBy
    }
}

# Windows Update Client AutoUpdate Status via COM object if accessible
$AutoUpdateEnabled = $null
try {
    $au = New-Object -ComObject Microsoft.Update.AutoUpdate
    $AutoUpdateEnabled = $au.ServiceEnabled
} catch {
    $AutoUpdateEnabled = "Unavailable"
}

$Result = [PSCustomObject]@{
    Services          = @($Services)
    RecentHotfixes    = @($Hotfixes)
    AutoUpdateEnabled = $AutoUpdateEnabled
    Timestamp         = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
}

if ($AsJson) {
    $Result | ConvertTo-Json -Depth 4
} else {
    $Result
}

