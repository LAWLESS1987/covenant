# ops/headscale_lan_path.ps1 -- headscale reachable on the home LAN from the new PC (TETSU) ONLY (2026-10-31).
#
# His words: "on its own and both those options", then "i said greenlight". Headscale runs in WSL on
# 127.0.0.1:8080. This forwards ONE laptop port to it, and lets in ONE remote address. It must be run BY HIM,
# as Administrator: it changes Windows networking and the firewall, which Claude does not do.
#
#   Add:     powershell -ExecutionPolicy Bypass -File ops\headscale_lan_path.ps1 -ListenAddr <this PC's LAN IP> -Peer <TETSU's LAN IP>
#   Remove:  powershell -ExecutionPolicy Bypass -File ops\headscale_lan_path.ps1 -ListenAddr <same> -Peer <same> -Remove
#
# THE ADDRESSES ARE PARAMETERS, NOT IN THIS FILE. This repository is public, and his home-network addresses are
# operation security (the same rule as ops/local_peers.txt). As first written they were constants here, and the
# opsec pre-push guard refused the push. That version is kept on the local branch
# lan-script-with-addresses-as-written-2026-10-31 and in .trash, never pushed.
#
# What it does, and nothing else:
#   1. a port forward  <ListenAddr>:8444 -> 127.0.0.1:8080  (netsh interface portproxy)
#   2. one inbound firewall rule: TCP 8444, Private profile, remote address <Peer> only
# TETSU's second tailscaled then logs in with  --login-server http://<ListenAddr>:8444
# Plain HTTP on the LAN: the Tailscale control protocol runs its own Noise encryption inside it, and the rule
# admits only TETSU. A home router that hands either PC a new address breaks it until the addresses are fixed.
# The rule is PRIVATE-profile only, on purpose: on a Public network (a cafe), <Peer> could be anyone. Measured
# 2026-10-31: this laptop's Wi-Fi is on the PUBLIC profile, so the rule admits nobody until he sets the home Wi-Fi to
# Private (Settings > Network & internet > Wi-Fi > this network > Private). That is his setting to change.
param(
    [Parameter(Mandatory = $true)][string]$ListenAddr,
    [Parameter(Mandatory = $true)][string]$Peer,
    [switch]$Remove
)

foreach ($a in @($ListenAddr, $Peer)) {
    if (-not ($a -as [System.Net.IPAddress]) -or $a -notmatch '^\d{1,3}(\.\d{1,3}){3}$') {
        Write-Host "Not an IPv4 address: $a"; exit 1
    }
}
$ListenPort = 8444
$RuleName   = "Covenant headscale LAN (TETSU only)"

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { Write-Host "Run this as Administrator."; exit 1 }

if ($Remove) {
    netsh interface portproxy delete v4tov4 listenaddress=$ListenAddr listenport=$ListenPort | Out-Null
    Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    Write-Host "Removed: the port forward and the firewall rule."
    exit 0
}

netsh interface portproxy add v4tov4 listenaddress=$ListenAddr listenport=$ListenPort `
    connectaddress=127.0.0.1 connectport=8080 | Out-Null
if (-not (Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $RuleName -Direction Inbound -Action Allow -Protocol TCP `
        -LocalPort $ListenPort -RemoteAddress $Peer -Profile Private | Out-Null
}
Write-Host "Added. Forward:"; netsh interface portproxy show v4tov4
Get-NetFirewallRule -DisplayName $RuleName | Get-NetFirewallAddressFilter | Format-List RemoteAddress
$p = (Get-NetConnectionProfile | Where-Object { $_.IPv4Connectivity -ne 'Disconnected' } | Select-Object -First 1).NetworkCategory
Write-Host "This network's profile: $p (the rule applies only if it is Private)."
try { $r = Invoke-WebRequest "http://$ListenAddr`:$ListenPort/health" -UseBasicParsing -TimeoutSec 5
      Write-Host "headscale through the forward: $($r.StatusCode) $([Text.Encoding]::UTF8.GetString($r.Content))" }
catch { Write-Host "headscale did not answer through the forward: $($_.Exception.Message)" }
