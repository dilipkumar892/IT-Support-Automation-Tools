"""
Network Diagnostics Engine
Performs ICMP pings, DNS queries, gateway detection, TCP port checks,
HTTP connectivity tests, and delivers actionable troubleshooting diagnoses.
"""

import socket
import urllib.request
import time
import subprocess
import re
from typing import Dict, Any, List, Optional, Tuple

from .safety import sanitize_hostname_or_ip, safe_subprocess_run


def test_dns_resolution(hostnames: Optional[List[str]] = None) -> Dict[str, Any]:
    """Tests resolution of provided or common hostnames."""
    targets = hostnames or ["google.com", "microsoft.com", "cloudflare.com"]
    results = {}
    success_count = 0

    for host in targets:
        try:
            start_t = time.perf_counter()
            ips = socket.gethostbyname_ex(host)[2]
            elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
            results[host] = {
                "success": True,
                "ips": ips,
                "latency_ms": elapsed_ms,
                "error": None
            }
            success_count += 1
        except Exception as e:
            results[host] = {
                "success": False,
                "ips": [],
                "latency_ms": None,
                "error": str(e)
            }

    status = "OK" if success_count == len(targets) else ("DEGRADED" if success_count > 0 else "FAIL")
    return {
        "status": status,
        "success_count": success_count,
        "total_targets": len(targets),
        "details": results
    }


def get_default_gateway() -> Optional[str]:
    """Detects default network gateway IP address using route print or netsh."""
    try:
        ret, stdout, _ = safe_subprocess_run(["route", "print", "0.0.0.0"], timeout_sec=5)
        if ret == 0:
            lines = stdout.splitlines()
            for line in lines:
                parts = line.strip().split()
                # Line matching 0.0.0.0 0.0.0.0 <gateway> <interface> <metric>
                if len(parts) >= 5 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                    gw = parts[2]
                    if sanitize_hostname_or_ip(gw):
                        return gw
    except Exception:
        pass
    return None


def ping_host(host: str, count: int = 4, timeout_sec: int = 2) -> Dict[str, Any]:
    """Executes safe standard ping on Windows."""
    if not sanitize_hostname_or_ip(host):
        return {
            "success": False,
            "host": host,
            "packets_sent": 0,
            "packets_received": 0,
            "packet_loss_percent": 100.0,
            "avg_latency_ms": None,
            "error": "Invalid or unsafe hostname/IP address."
        }

    cmd = ["ping", "-n", str(count), "-w", str(timeout_sec * 1000), host]
    code, stdout, stderr = safe_subprocess_run(cmd, timeout_sec=count * timeout_sec + 5)

    if code != 0 and not stdout:
        return {
            "success": False,
            "host": host,
            "packets_sent": count,
            "packets_received": 0,
            "packet_loss_percent": 100.0,
            "avg_latency_ms": None,
            "error": stderr or "Host unreachable"
        }

    # Parse ping metrics from Windows output
    # Example: Packets: Sent = 4, Received = 4, Lost = 0 (0% loss)
    sent = count
    received = 0
    loss_percent = 100.0
    avg_ms = None

    loss_match = re.search(r"Lost = \d+ \((\d+)% loss\)", stdout)
    if loss_match:
        loss_percent = float(loss_match.group(1))
        received = int(sent * (100.0 - loss_percent) / 100.0)

    avg_match = re.search(r"Average = (\d+)ms", stdout)
    if avg_match:
        avg_ms = float(avg_match.group(1))

    return {
        "success": received > 0,
        "host": host,
        "packets_sent": sent,
        "packets_received": received,
        "packet_loss_percent": loss_percent,
        "avg_latency_ms": avg_ms,
        "raw_output": stdout.strip(),
        "error": None if received > 0 else "Destination host unreachable"
    }


def test_tcp_port(host: str, port: int, timeout_sec: float = 3.0) -> Dict[str, Any]:
    """Tests if a TCP socket connection can be established."""
    if not sanitize_hostname_or_ip(host):
        return {"success": False, "host": host, "port": port, "error": "Invalid host"}

    start_t = time.perf_counter()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout_sec)
    try:
        sock.connect((host, port))
        latency = round((time.perf_counter() - start_t) * 1000, 2)
        sock.close()
        return {
            "success": True,
            "host": host,
            "port": port,
            "latency_ms": latency,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "host": host,
            "port": port,
            "latency_ms": None,
            "error": str(e)
        }


def test_http_connectivity(url: str = "https://www.msftconnecttest.com/connecttest.txt", timeout_sec: int = 5) -> Dict[str, Any]:
    """Tests web connectivity via HTTP/HTTPS request."""
    start_t = time.perf_counter()
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "IT-Support-Automation-Suite/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            code = resp.getcode()
            elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
            return {
                "success": (200 <= code < 400),
                "url": url,
                "status_code": code,
                "latency_ms": elapsed_ms,
                "error": None
            }
    except Exception as e:
        return {
            "success": False,
            "url": url,
            "status_code": None,
            "latency_ms": None,
            "error": str(e)
        }


def flush_dns() -> Tuple[bool, str]:
    """Executes ipconfig /flushdns safely."""
    code, out, err = safe_subprocess_run(["ipconfig", "/flushdns"], timeout_sec=10)
    success = (code == 0)
    message = out.strip() if success else (err.strip() or "Failed to flush DNS cache")
    return (success, message)


def run_comprehensive_network_diagnostics() -> Dict[str, Any]:
    """
    Runs an end-to-end network assessment, isolates failures, and returns
    clear, actionable diagnostic findings.
    """
    gateway = get_default_gateway()
    gw_result = ping_host(gateway, count=2) if gateway else None
    dns_result = test_dns_resolution(["google.com", "microsoft.com", "cloudflare.com"])
    internet_ping = ping_host("1.1.1.1", count=3)
    http_result = test_http_connectivity()

    # Determine diagnosis and recommended actions
    findings = []
    recommendations = []
    overall_status = "PASS"

    if not gateway:
        overall_status = "CRITICAL"
        findings.append("No default network gateway detected.")
        recommendations.append("Check physical Ethernet cable or WiFi connection status.")
        recommendations.append("Verify if DHCP is enabled or an IP address is statically assigned.")
    elif gw_result and not gw_result["success"]:
        overall_status = "CRITICAL"
        findings.append(f"Default gateway ({gateway}) is not responding to ICMP ping.")
        recommendations.append("Restart local router / switch or contact local network admin.")
    else:
        findings.append(f"Default gateway ({gateway}) is reachable (Latency: {gw_result.get('avg_latency_ms', 'N/A')}ms).")

    if internet_ping["success"]:
        findings.append(f"External IP connectivity (1.1.1.1) is operational (Latency: {internet_ping.get('avg_latency_ms', 'N/A')}ms).")
    else:
        if overall_status != "CRITICAL":
            overall_status = "WARNING"
        findings.append("Cannot reach external IP address 1.1.1.1 directly.")
        recommendations.append("Check firewall or ISP upstream routing.")

    if dns_result["status"] == "OK":
        findings.append("DNS resolution is fully functional.")
    elif dns_result["status"] == "DEGRADED":
        if overall_status == "PASS":
            overall_status = "WARNING"
        findings.append("DNS resolution is degraded (some targets failed).")
        recommendations.append("Run DNS cache flush or test alternative DNS servers (e.g. 1.1.1.1 / 8.8.8.8).")
    else:
        if overall_status != "CRITICAL":
            overall_status = "CRITICAL"
        findings.append("DNS resolution failed for all test domains.")
        recommendations.append("Verify DNS server addresses in adapter settings (ipconfig /all).")
        recommendations.append("Execute 'ipconfig /flushdns' and 'ipconfig /registerdns'.")

    if http_result["success"]:
        findings.append(f"Web connectivity check passed (Latency: {http_result['latency_ms']}ms).")
    else:
        if overall_status == "PASS":
            overall_status = "WARNING"
        findings.append(f"HTTP connectivity failed: {http_result['error']}")
        recommendations.append("Check enterprise web proxy or captive portal requirements.")

    return {
        "status": overall_status,
        "gateway": gateway,
        "gateway_ping": gw_result,
        "dns": dns_result,
        "internet_ping": internet_ping,
        "http": http_result,
        "findings": findings,
        "recommendations": recommendations,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

