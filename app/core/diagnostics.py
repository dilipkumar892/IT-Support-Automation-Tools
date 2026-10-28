"""
Windows Diagnostics and Troubleshooting Engine
Implements SFC, DISM, Event Log auditing, Disk analysis, Service checks,
Startup applications inspection, and Windows Update health verification.
"""

import os
import sys
import psutil
from typing import Dict, Any, List, Optional
from datetime import datetime

from .safety import is_admin, safe_subprocess_run


def run_sfc_scan(repair_mode: bool = False) -> Dict[str, Any]:
    """
    Executes Windows System File Checker (SFC).
    repair_mode=False runs /VERIFYONLY (read-only, does not alter files).
    repair_mode=True runs /SCANNOW (repairs corrupted files, requires admin & confirmation).
    """
    if not is_admin():
        return {
            "success": False,
            "exit_code": 1,
            "mode": "repair" if repair_mode else "verify_only",
            "message": "Administrator privileges required to execute SFC.",
            "output": ""
        }

    flag = "/scannow" if repair_mode else "/verifyonly"
    cmd = ["sfc.exe", flag]
    # SFC can take several minutes; set generous timeout
    code, stdout, stderr = safe_subprocess_run(cmd, timeout_sec=600, check_elevation=True)

    # Interpreting common SFC results
    # 0 = No integrity violations found
    # 1 = System file integrity violations found
    is_clean = ("did not find any integrity violations" in stdout.lower())
    repaired = ("successfully repaired them" in stdout.lower())

    summary = "System integrity check completed."
    if is_clean:
        summary = "Windows Resource Protection did not find any integrity violations."
    elif repaired:
        summary = "Corrupt files were found and successfully repaired."
    elif "found corrupt files but was unable to fix" in stdout.lower():
        summary = "Corrupt files were detected but could not be automatically repaired (DISM recommended)."

    return {
        "success": (code == 0 or is_clean or repaired),
        "exit_code": code,
        "mode": "repair" if repair_mode else "verify_only",
        "summary": summary,
        "output": stdout if stdout else stderr
    }


def run_dism_health(operation: str = "check") -> Dict[str, Any]:
    """
    Executes DISM (Deployment Image Servicing and Management).
    operation:
      - 'check': /CheckHealth (instant check of corruption flag)
      - 'scan': /ScanHealth (thorough scan)
      - 'restore': /RestoreHealth (online repair via Windows Update)
    """
    if not is_admin():
        return {
            "success": False,
            "exit_code": 1,
            "operation": operation,
            "message": "Administrator privileges required to execute DISM.",
            "output": ""
        }

    flag_map = {
        "check": "/CheckHealth",
        "scan": "/ScanHealth",
        "restore": "/RestoreHealth"
    }
    flag = flag_map.get(operation, "/CheckHealth")
    cmd = ["dism.exe", "/Online", "/Cleanup-Image", flag]

    timeout = 180 if operation == "check" else 900
    code, stdout, stderr = safe_subprocess_run(cmd, timeout_sec=timeout, check_elevation=True)

    corrupt_detected = ("corruption has been detected" in stdout.lower() or "repairable" in stdout.lower())
    healthy = ("no component store corruption detected" in stdout.lower())

    return {
        "success": (code == 0),
        "exit_code": code,
        "operation": operation,
        "corrupt_detected": corrupt_detected,
        "healthy": healthy,
        "output": stdout if stdout else stderr
    }


def analyze_disk_cleanup_targets() -> Dict[str, Any]:
    """
    Calculates sizes of common temporary caches without deleting anything.
    Identifies Windows Temp, User Temp, and Recycle Bin estimates safely.
    """
    targets = []
    total_bytes = 0

    user_temp = os.environ.get("TEMP", "")
    if user_temp and os.path.exists(user_temp):
        size = 0
        file_count = 0
        try:
            for root, _, files in os.walk(user_temp):
                for f in files:
                    try:
                        fp = os.path.join(root, f)
                        size += os.path.getsize(fp)
                        file_count += 1
                    except OSError:
                        pass
        except Exception:
            pass
        mb = round(size / (1024 * 1024), 2)
        total_bytes += size
        targets.append({
            "name": "User Temp Folder",
            "path": user_temp,
            "size_mb": mb,
            "file_count": file_count
        })

    win_temp = r"C:\Windows\Temp"
    if os.path.exists(win_temp):
        size = 0
        file_count = 0
        try:
            for root, _, files in os.walk(win_temp):
                for f in files:
                    try:
                        fp = os.path.join(root, f)
                        size += os.path.getsize(fp)
                        file_count += 1
                    except OSError:
                        pass
        except Exception:
            pass
        mb = round(size / (1024 * 1024), 2)
        total_bytes += size
        targets.append({
            "name": "Windows System Temp",
            "path": win_temp,
            "size_mb": mb,
            "file_count": file_count
        })

    return {
        "targets": targets,
        "total_reclaimable_mb": round(total_bytes / (1024 * 1024), 2),
        "timestamp": datetime.now().isoformat()
    }


def inspect_windows_services() -> Dict[str, Any]:
    """
    Inspects critical Windows services (wuauserv, bits, cryptsvc, lanmanserver, spooler).
    """
    critical_services = ["wuauserv", "bits", "cryptsvc", "Dhcp", "Dnscache", "Spooler"]
    service_status = {}

    for s_name in critical_services:
        try:
            svc = psutil.win_service_get(s_name)
            s_dict = svc.as_dict()
            service_status[s_name] = {
                "display_name": s_dict.get("display_name", s_name),
                "status": s_dict.get("status", "unknown"),
                "start_type": s_dict.get("start_type", "unknown")
            }
        except Exception as e:
            service_status[s_name] = {
                "display_name": s_name,
                "status": "not_found",
                "error": str(e)
            }

    return {
        "services": service_status,
        "timestamp": datetime.now().isoformat()
    }


def inspect_startup_programs() -> List[Dict[str, str]]:
    """Inspects startup applications from Windows Registry Run keys."""
    results: List[Dict[str, str]] = []
    if sys.platform != "win32":
        return results

    try:
        import winreg
        run_keys = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "User (Current)"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "All Users (64-bit)"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "All Users (32-bit)")
        ]

        for root_key, subkey, scope in run_keys:
            try:
                key = winreg.OpenKey(root_key, subkey, 0, winreg.KEY_READ)
                num_values = winreg.QueryInfoKey(key)[1]
                for i in range(num_values):
                    val_name, val_data, _ = winreg.EnumValue(key, i)
                    results.append({
                        "name": val_name,
                        "command": str(val_data),
                        "scope": scope
                    })
                winreg.CloseKey(key)
            except OSError:
                pass
    except Exception:
        pass

    return results


def collect_recent_event_log_errors(max_events: int = 15) -> List[Dict[str, Any]]:
    """
    Collects recent System and Application error/warning events safely
    using wevtutil query.
    """
    events: List[Dict[str, Any]] = []
    if sys.platform != "win32":
        return events

    # Safe wevtutil query for Error (level=2) and Critical (level=1) in System channel
    query_cmd = [
        "wevtutil", "qe", "System",
        "/q:*[System[(Level=1 or Level=2)]]",
        "/c:10",
        "/rd:true",
        "/f:text"
    ]

    code, stdout, _ = safe_subprocess_run(query_cmd, timeout_sec=15)
    if code == 0 and stdout:
        raw_entries = stdout.split("Event[")
        for entry in raw_entries:
            if not entry.strip():
                continue
            lines = entry.strip().splitlines()
            log_item = {"channel": "System", "level": "Error/Critical", "raw": entry.strip()[:400]}
            for line in lines:
                if line.startswith("Date:"):
                    log_item["date"] = line.replace("Date:", "").strip()
                elif line.startswith("Source:"):
                    log_item["source"] = line.replace("Source:", "").strip()
                elif line.startswith("Event ID:"):
                    log_item["event_id"] = line.replace("Event ID:", "").strip()
            events.append(log_item)

    return events[:max_events]


def get_top_resource_consumers(limit: int = 5) -> Dict[str, List[Dict[str, Any]]]:
    """Identifies top CPU and memory consuming processes."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            info = proc.info
            processes.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    top_cpu = sorted(processes, key=lambda p: p.get('cpu_percent') or 0.0, reverse=True)[:limit]
    top_mem = sorted(processes, key=lambda p: p.get('memory_percent') or 0.0, reverse=True)[:limit]

    return {
        "top_cpu": top_cpu,
        "top_memory": top_mem
    }


def fix_print_spooler_service() -> Dict[str, Any]:
    r"""
    Stops the Print Spooler service, purges all pending stuck jobs from
    C:\Windows\System32\spool\PRINTERS, and restarts the service.
    Requires Administrator privileges (UAC).
    """
    if not is_admin():
        return {
            "success": False,
            "message": "Administrator privileges required to manage Print Spooler service."
        }

    # 1. Stop spooler service
    safe_subprocess_run(["net", "stop", "spooler"], timeout_sec=15, check_elevation=True)

    # 2. Purge pending spool files
    spool_dir = r"C:\Windows\System32\spool\PRINTERS"
    deleted_files = 0
    if os.path.exists(spool_dir):
        try:
            for item in os.listdir(spool_dir):
                item_path = os.path.join(spool_dir, item)
                try:
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                        deleted_files += 1
                except OSError:
                    pass
        except Exception:
            pass

    # 3. Start spooler service
    code, stdout, stderr = safe_subprocess_run(["net", "start", "spooler"], timeout_sec=15, check_elevation=True)
    is_running = ("started successfully" in stdout.lower() or code == 0)

    return {
        "success": is_running,
        "deleted_spool_jobs": deleted_files,
        "service_status": "Running" if is_running else "Stopped",
        "output": stdout if is_running else stderr
    }


def reset_network_adapter_and_stack() -> Dict[str, Any]:
    """
    Performs full TCP/IP stack reset, Winsock catalog reinitialization,
    and DNS cache flush.
    Requires Administrator privileges (UAC).
    """
    if not is_admin():
        return {
            "success": False,
            "message": "Administrator privileges required to reset network stack."
        }

    outputs = []
    # 1. Flush DNS
    _, out_dns, _ = safe_subprocess_run(["ipconfig", "/flushdns"], timeout_sec=10)
    outputs.append(out_dns.strip())

    # 2. Winsock reset
    _, out_ws, _ = safe_subprocess_run(["netsh", "winsock", "reset"], timeout_sec=15)
    outputs.append(out_ws.strip())

    # 3. TCP/IP reset
    _, out_ip, _ = safe_subprocess_run(["netsh", "int", "ip", "reset"], timeout_sec=15)
    outputs.append(out_ip.strip())

    return {
        "success": True,
        "message": "Network stack and Winsock catalog successfully reset.",
        "details": outputs,
        "reboot_recommended": True
    }


def reset_windows_update_agent() -> Dict[str, Any]:
    """
    Stops update services (wuauserv, bits, cryptsvc), purges temporary download
    caches in SoftwareDistribution, and restarts update services.
    Requires Administrator privileges (UAC).
    """
    if not is_admin():
        return {
            "success": False,
            "message": "Administrator privileges required to reset Windows Update components."
        }

    services = ["wuauserv", "bits", "cryptsvc"]
    for s in services:
        safe_subprocess_run(["net", "stop", s], timeout_sec=15)

    # Clean SoftwareDistribution download cache
    download_dir = r"C:\Windows\SoftwareDistribution\Download"
    purged_count = 0
    if os.path.exists(download_dir):
        try:
            for item in os.listdir(download_dir):
                item_path = os.path.join(download_dir, item)
                try:
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                        purged_count += 1
                except OSError:
                    pass
        except Exception:
            pass

    # Restart services
    for s in services:
        safe_subprocess_run(["net", "start", s], timeout_sec=15)

    return {
        "success": True,
        "message": "Windows Update services reset and download cache cleared.",
        "purged_download_files": purged_count
    }


def generate_battery_report() -> Dict[str, Any]:
    """
    Generates a battery health assessment using powercfg /batteryreport or CIM.
    Runs in Standard User context (Normal Rights).
    """
    import tempfile
    import re

    battery_info = {
        "has_battery": False,
        "design_capacity_mwh": None,
        "full_charge_capacity_mwh": None,
        "battery_wear_percent": 0.0,
        "health_assessment": "AC Desktop or Virtual Machine (No battery detected)",
        "cycle_count": None
    }

    if sys.platform != "win32":
        return battery_info

    # Generate battery report into temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        report_html = os.path.join(tmpdir, "battery_report.html")
        code, _, _ = safe_subprocess_run(["powercfg", "/batteryreport", "/output", report_html], timeout_sec=15)

        if code == 0 and os.path.exists(report_html):
            try:
                with open(report_html, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Extract design capacity & full charge capacity
                design_match = re.search(r"DESIGN CAPACITY[^\d]*(\d[\d,]+)\s*mWh", content, re.IGNORECASE)
                full_match = re.search(r"FULL CHARGE CAPACITY[^\d]*(\d[\d,]+)\s*mWh", content, re.IGNORECASE)
                cycle_match = re.search(r"CYCLE COUNT[^\d]*(\d+)", content, re.IGNORECASE)

                if design_match and full_match:
                    design_cap = int(design_match.group(1).replace(",", ""))
                    full_cap = int(full_match.group(1).replace(",", ""))

                    if design_cap > 0:
                        wear = round(max(0.0, ((design_cap - full_cap) / design_cap) * 100.0), 1)
                        battery_info["has_battery"] = True
                        battery_info["design_capacity_mwh"] = design_cap
                        battery_info["full_charge_capacity_mwh"] = full_cap
                        battery_info["battery_wear_percent"] = wear

                        if wear < 15.0:
                            health = "Excellent - Healthy Battery"
                        elif wear < 35.0:
                            health = "Fair - Normal Operational Degradation"
                        else:
                            health = "Degraded - Battery Replacement Recommended"

                        battery_info["health_assessment"] = health

                if cycle_match:
                    battery_info["cycle_count"] = int(cycle_match.group(1))

            except Exception:
                pass

    return battery_info


def clean_junk_files(system_level: bool = False) -> Dict[str, Any]:
    r"""
    Cleans temporary caches and crash dumps safely.
    system_level=False: User %TEMP% (Normal Rights)
    system_level=True: C:\Windows\Temp and system WER queues (Requires UAC)
    """
    if system_level and not is_admin():
        return {
            "success": False,
            "message": "Administrator privileges required for system-level cleanup."
        }

    targets = []
    if not system_level:
        user_temp = os.environ.get("TEMP", "")
        if user_temp and os.path.exists(user_temp):
            targets.append(user_temp)
    else:
        targets.extend([r"C:\Windows\Temp", r"C:\ProgramData\Microsoft\Windows\WER\ReportQueue"])

    deleted_count = 0
    reclaimed_bytes = 0

    for folder in targets:
        if not os.path.exists(folder):
            continue
        try:
            for root, dirs, files in os.walk(folder, topdown=False):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        sz = os.path.getsize(fp)
                        os.remove(fp)
                        reclaimed_bytes += sz
                        deleted_count += 1
                    except (PermissionError, OSError):
                        pass  # Safely ignore locked in-use files
        except Exception:
            pass

    return {
        "success": True,
        "system_level": system_level,
        "files_removed": deleted_count,
        "reclaimed_mb": round(reclaimed_bytes / (1024 * 1024), 2),
        "message": f"Cleaned {deleted_count} files, reclaiming {round(reclaimed_bytes / (1024 * 1024), 2)} MB."
    }


def audit_domain_and_identity() -> Dict[str, Any]:
    """
    Inspects Active Directory domain membership, secure channel trust,
    and Microsoft Entra ID (Azure AD) device registration state.
    Runs in Standard User context (Normal Rights).
    """
    result = {
        "domain_joined": False,
        "domain_name": "WORKGROUP",
        "azure_ad_joined": False,
        "enterprise_joined": False,
        "tenant_name": "",
        "user_upn": "",
        "secure_channel_ok": True,
        "details": ""
    }

    if sys.platform != "win32":
        return result

    # 1. Check computer system domain via environment / platform
    domain = os.environ.get("USERDNSDOMAIN") or os.environ.get("USERDOMAIN", "WORKGROUP")
    result["domain_name"] = domain
    if domain != "WORKGROUP" and domain != os.environ.get("COMPUTERNAME", ""):
        result["domain_joined"] = True

    # 2. Query dsregcmd /status for Entra ID registration
    code, stdout, _ = safe_subprocess_run(["dsregcmd", "/status"], timeout_sec=10)
    if code == 0 and stdout:
        for line in stdout.splitlines():
            s = line.strip()
            if s.startswith("AzureAdJoined :"):
                result["azure_ad_joined"] = "YES" in s.upper()
            elif s.startswith("EnterpriseJoined :"):
                result["enterprise_joined"] = "YES" in s.upper()
            elif s.startswith("TenantName :"):
                result["tenant_name"] = s.replace("TenantName :", "").strip()
            elif s.startswith("UserPrincipalName :"):
                result["user_upn"] = s.replace("UserPrincipalName :", "").strip()

    return result


def audit_bitlocker_status() -> Dict[str, Any]:
    """
    Checks BitLocker drive encryption status, protection state, and cipher algorithm.
    Requires Administrator privileges (UAC).
    """
    if not is_admin():
        return {
            "success": False,
            "message": "Administrator privileges required to query BitLocker status."
        }

    code, stdout, stderr = safe_subprocess_run(["manage-bde", "-status", "C:"], timeout_sec=15, check_elevation=True)
    if code != 0:
        return {
            "success": False,
            "message": stderr or "Failed to query BitLocker status.",
            "output": ""
        }

    protection_on = ("protection on" in stdout.lower() or "protection status:    protection on" in stdout.lower())
    encrypted = ("100.0%" in stdout or "fully encrypted" in stdout.lower())

    return {
        "success": True,
        "protection_on": protection_on,
        "fully_encrypted": encrypted,
        "summary": "BitLocker Protection: ON" if protection_on else "BitLocker Protection: OFF (Vulnerable)",
        "output": stdout.strip()
    }


def generate_itsm_ticket_payload(system_snapshot=None, diag_report=None) -> Dict[str, str]:
    """
    Builds pre-formatted ticket content in Markdown, Jira Markup, and Plain Text
    ready to paste directly into ServiceNow, Jira Service Management, or Zendesk.
    Runs in Standard User context (Normal Rights).
    """
    import socket
    from .system_info import (
        get_windows_version_details,
        get_cpu_info,
        get_memory_info,
        get_disks_info,
        get_logged_in_user
    )

    host = system_snapshot.hostname if system_snapshot else socket.gethostname()
    os_info = get_windows_version_details()
    cpu = get_cpu_info()
    mem = get_memory_info()
    disks = get_disks_info()
    user = get_logged_in_user()

    c_drive = next((d for d in disks if d.mountpoint.upper().startswith("C:")), None)
    c_info = f"{c_drive.free_gb} GB Free of {c_drive.total_gb} GB ({c_drive.percent_used}% Used)" if c_drive else "N/A"

    findings_text = ""
    if diag_report and diag_report.findings:
        findings_text = "\n".join([f"- {f.get('item', str(f))}" for f in diag_report.findings[:5]])
    else:
        findings_text = "- Automated diagnostics executed; all standard health checks within normal thresholds."

    # Markdown format
    markdown = f"""### IT Support Diagnostic Ticket
* **Device**: `{host}`
* **Operating System**: {os_info['os_name']} (Build {os_info['os_build']})
* **User**: `{user}`
* **Processor**: {cpu['model']} ({cpu['cores_logical']} Cores)
* **Memory**: {mem['used_gb']} GB Used of {mem['total_gb']} GB ({mem['percent_used']}%)
* **Storage (C:)**: {c_info}

#### Diagnostic Findings:
{findings_text}
"""

    # Jira markup format
    jira = f"""h3. IT Support Diagnostic Ticket
* *Device*: {{color:#0052cc}}{host}{{color}}
* *OS*: {os_info['os_name']} (Build {os_info['os_build']})
* *User*: {user}
* *Memory*: {mem['used_gb']} GB / {mem['total_gb']} GB
* *Storage (C:)*: {c_info}

h4. Diagnostic Findings:
{findings_text}
"""

    # Plain text format
    plain = f"""IT SUPPORT TICKET SUMMARY
Device: {host}
OS: {os_info['os_name']} ({os_info['os_build']})
User: {user}
CPU: {cpu['model']}
RAM: {mem['used_gb']}GB used of {mem['total_gb']}GB
Disk C: {c_info}
Diagnostic Summary:
{findings_text}
"""

    return {
        "markdown": markdown,
        "jira": jira,
        "plain": plain
    }


