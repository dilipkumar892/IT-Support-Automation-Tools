<#
.SYNOPSIS
    Performs comprehensive Windows network diagnostics.
.DESCRIPTION
    Tests active network adapters, gateway ping, DNS resolution, internet connectivity,
    and returns a structured diagnostic report in JSON.
.EXAMPLE
    .\network_diagnostics.ps1 -AsJson
#>

[CmdletBinding()]
param (
    [switch]$AsJson = $true,
    [string[]]$DnsTargets = @("google.com", "microsoft.com"),
    [string[]]$PingTargets = @("1.1.1.1", "8.8.8.8")
)

$ErrorActionPreference = "SilentlyContinue"

# Active Network Adapters
$Adapters = Get-NetAdapter | Where-Object { $_.Status -eq "Up" } | ForEach-Object {
    $ipConfig = Get-NetIPAddress -InterfaceIndex $_.ifIndex -AddressFamily IPv4 2>$null
    [PSCustomObject]@{
        Name          = $_.Name
        InterfaceDesc = $_.InterfaceDescription
        MacAddress    = $_.MacAddress
        LinkSpeed     = $_.LinkSpeed
        IPv4Address   = ($ipConfig.IPAddress -join ", ")
        Status        = $_.Status
    }
}

# Gateway Detection and Ping
$DefaultRoute = Get-NetRoute -DestinationPrefix "0.0.0.0/0" | Sort-Object RouteMetric | Select-Object -First 1
$GatewayIP = $DefaultRoute.NextHop
$GatewayPingSuccess = $false
$GatewayLatencyMs = $null

if ($GatewayIP -and $GatewayIP -ne "0.0.0.0") {
    $gwPing = Test-Connection -ComputerName $GatewayIP -Count 2 -Quiet
    $GatewayPingSuccess = $gwPing
}

# DNS Test
$DnsResults = @()
foreach ($target in $DnsTargets) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $resolved = $false
    $ips = @()
    try {
        $entry = [System.Net.Dns]::GetHostEntry($target)
        $ips = $entry.AddressList | ForEach-Object { $_.IPAddressToString }
        $resolved = ($ips.Count -gt 0)
    } catch {}
    $sw.Stop()

    $DnsResults += [PSCustomObject]@{
        Target      = $target
        Resolved    = $resolved
        Addresses   = $ips
        LatencyMs   = [math]::Round($sw.Elapsed.TotalMilliseconds, 2)
    }
}

# Internet Ping
$PingResults = @()
foreach ($ip in $PingTargets) {
    $p = Test-Connection -ComputerName $ip -Count 2 2>$null
    $success = ($p -and $p.Count -gt 0)
    $avgMs = if ($success) { ($p | Measure-Object -Property ResponseTime -Average).Average } else { $null }

    $PingResults += [PSCustomObject]@{
        Target      = $ip
        Success     = $success
        AvgLatencyMs = if ($avgMs) { [math]::Round($avgMs, 1) } else { $null }
    }
}

$Result = [PSCustomObject]@{
    ActiveAdapters     = @($Adapters)
    DefaultGateway     = $GatewayIP
    GatewayPingSuccess = $GatewayPingSuccess
    DnsTests           = @($DnsResults)
    PingTests          = @($PingResults)
    Timestamp          = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
}

if ($AsJson) {
    $Result | ConvertTo-Json -Depth 4
} else {
    $Result
}

