<#
.SYNOPSIS
    Gathers detailed Windows system diagnostic information safely.
.DESCRIPTION
    Collects operating system build, computer model, CPU metrics, memory status,
    and event log warnings/errors in the last 24 hours. Returns structured JSON.
.EXAMPLE
    .\system_diagnostics.ps1 -AsJson
#>

[CmdletBinding()]
param (
    [switch]$AsJson = $true,
    [int]$HoursToScan = 24
)

$ErrorActionPreference = "SilentlyContinue"

$ComputerName = $env:COMPUTERNAME
$OS = Get-CimInstance -ClassName Win32_OperatingSystem
$CS = Get-CimInstance -ClassName Win32_ComputerSystem
$CPU = Get-CimInstance -ClassName Win32_Processor | Select-Object -First 1

# Calculate Uptime
$LastBoot = $OS.LastBootUpTime
$Uptime = if ($LastBoot) { (Get-Date) - $LastBoot } else { $null }

# Disk Information
$Disks = Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
    [PSCustomObject]@{
        DeviceID       = $_.DeviceID
        VolumeName     = $_.VolumeName
        FileSystem     = $_.FileSystem
        TotalSizeGB    = [math]::Round($_.Size / 1GB, 2)
        FreeSpaceGB    = [math]::Round($_.FreeSpace / 1GB, 2)
        PercentUsed    = [math]::Round((($_.Size - $_.FreeSpace) / $_.Size) * 100, 1)
    }
}

# Recent System Errors (Past 24 Hours)
$CutoffTime = (Get-Date).AddHours(-$HoursToScan)
$RecentErrors = Get-WinEvent -FilterHashtable @{
    LogName   = 'System'
    Level     = 1, 2 # Critical, Error
    StartTime = $CutoffTime
} -MaxEvents 15 2>$null | ForEach-Object {
    [PSCustomObject]@{
        TimeCreated = $_.TimeCreated.ToString("yyyy-MM-dd HH:mm:ss")
        Provider    = $_.ProviderName
        Id          = $_.Id
        Message     = if ($_.Message) { $_.Message.Substring(0, [math]::Min(200, $_.Message.Length)) } else { "" }
    }
}

$Result = [PSCustomObject]@{
    ComputerName       = $ComputerName
    Manufacturer       = $CS.Manufacturer
    Model              = $CS.Model
    OSName             = $OS.Caption
    OSVersion          = $OS.Version
    OSBuild            = $OS.BuildNumber
    Architecture       = $OS.OSArchitecture
    Processor          = $CPU.Name
    LogicalCores       = $CPU.NumberOfLogicalProcessors
    TotalMemoryGB      = [math]::Round($CS.TotalPhysicalMemory / 1GB, 2)
    FreeMemoryGB       = [math]::Round($OS.FreePhysicalMemory / 1MB, 2)
    LastBootUpTime     = if ($LastBoot) { $LastBoot.ToString("yyyy-MM-dd HH:mm:ss") } else { "Unknown" }
    UptimeDays         = if ($Uptime) { [math]::Round($Uptime.TotalDays, 2) } else { 0 }
    Disks              = @($Disks)
    RecentSystemErrors = @($RecentErrors)
    Timestamp          = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
}

if ($AsJson) {
    $Result | ConvertTo-Json -Depth 4
} else {
    $Result
}

