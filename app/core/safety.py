"""
Safety and Security Module for IT Support Automation Suite
Ensures least-privilege, safe subprocess handling, input validation, and confirmation policies.
"""

import os
import sys
import re
import ctypes
import subprocess
from enum import Enum
from typing import List, Tuple, Optional, Dict, Any


class RiskLevel(Enum):
    READ_ONLY = "READ_ONLY"      # No system modifications (e.g. read event logs, ping, inspect)
    LOW = "LOW"                  # Non-destructive routine ops (e.g. flush DNS cache)
    MEDIUM = "MEDIUM"            # System diagnostic scans (e.g. SFC verify, DISM scan)
    HIGH_ADMIN = "HIGH_ADMIN"    # Modifies system files/services (e.g. SFC repair, DISM restore)


# Allowlisted tasks mapped to their safety parameters
TASK_ALLOWLIST: Dict[str, Dict[str, Any]] = {
    "collect_system_info": {
        "name": "Collect System Information",
        "risk": RiskLevel.READ_ONLY,
        "requires_admin": False,
        "service_type": "NORMAL",
        "description": "Gathers hardware, OS, and memory metrics without modifications."
    },
    "run_network_diagnostics": {
        "name": "Network Diagnostics",
        "risk": RiskLevel.READ_ONLY,
        "requires_admin": False,
        "service_type": "NORMAL",
        "description": "Tests connectivity, DNS resolution, and gateway availability."
    },
    "scan_installed_software": {
        "name": "Software Inventory Scan",
        "risk": RiskLevel.READ_ONLY,
        "requires_admin": False,
        "service_type": "NORMAL",
        "description": "Enumerates installed applications from registry."
    },
    "analyze_disk_space": {
        "name": "Analyze Disk Space",
        "risk": RiskLevel.READ_ONLY,
        "requires_admin": False,
        "service_type": "NORMAL",
        "description": "Calculates drive usage and identifies large temporary caches."
    },
    "clean_disk_junk": {
        "name": "Clean User Temporary Junk",
        "risk": RiskLevel.LOW,
        "requires_admin": False,
        "service_type": "NORMAL",
        "description": "Safely removes temporary files and crash logs from user profile."
    },
    "clean_system_junk": {
        "name": "Clean System-Wide Temporary Junk",
        "risk": RiskLevel.MEDIUM,
        "requires_admin": True,
        "service_type": "UAC_REQUIRED",
        "description": "Purges Windows System Temp, WER queues, and Windows rollback logs."
    },
    "sfc_verify_only": {
        "name": "SFC Integrity Check (Read-Only)",
        "risk": RiskLevel.MEDIUM,
        "requires_admin": True,
        "service_type": "UAC_REQUIRED",
        "description": "Scans Windows system files without applying automatic repairs."
    },
    "sfc_repair": {
        "name": "SFC System File Repair",
        "risk": RiskLevel.HIGH_ADMIN,
        "requires_admin": True,
        "service_type": "UAC_REQUIRED",
        "description": "Repairs corrupted Windows protected operating system files."
    },
    "dism_check_health": {
        "name": "DISM Check Health",
        "risk": RiskLevel.READ_ONLY,
        "requires_admin": True,
        "service_type": "UAC_REQUIRED",
        "description": "Quickly inspects component store corruption flags."
    },
    "dism_scan_health": {
        "name": "DISM Scan Health",
        "risk": RiskLevel.MEDIUM,
        "requires_admin": True,
        "service_type": "UAC_REQUIRED",
        "description": "Performs an in-depth scan of the Windows Component Store."
    },
    "dism_restore_health": {
        "name": "DISM Restore Health",
        "risk": RiskLevel.HIGH_ADMIN,
        "requires_admin": True,
        "service_type": "UAC_REQUIRED",
        "description": "Downloads and replaces damaged component store files from Windows Update."
    },
    "check_windows_updates": {
        "name": "Windows Update Diagnostics",
        "risk": RiskLevel.READ_ONLY,
        "requires_admin": False,
        "service_type": "NORMAL",
        "description": "Checks Windows Update client services and installed hotfixes."
    },
    "reset_windows_update_components": {
        "name": "Reset Windows Update Components",
        "risk": RiskLevel.HIGH_ADMIN,
        "requires_admin": True,
        "service_type": "UAC_REQUIRED",
        "description": "Stops update services, clears corrupted SoftwareDistribution cache, and restarts agent."
    },
    "audit_event_logs": {
        "name": "Event Log Audit",
        "risk": RiskLevel.READ_ONLY,
        "requires_admin": False,
        "service_type": "NORMAL",
        "description": "Collects critical system and application events from the last 24 hours."
    },
    "audit_startup_programs": {
        "name": "Startup Programs Audit",
        "risk": RiskLevel.READ_ONLY,
        "requires_admin": False,
        "service_type": "NORMAL",
        "description": "Lists applications configured to launch on user logon."
    },
    "flush_dns_cache": {
        "name": "Flush DNS Cache",
        "risk": RiskLevel.LOW,
        "requires_admin": True,
        "service_type": "UAC_REQUIRED",
        "description": "Clears and resets the contents of the DNS client resolver cache."
    },
    "reset_network_stack": {
        "name": "Reset Network Stack & Winsock",
        "risk": RiskLevel.HIGH_ADMIN,
        "requires_admin": True,
        "service_type": "UAC_REQUIRED",
        "description": "Performs flushdns, netsh winsock reset, and TCP/IP stack re-initialization."
    },
    "fix_print_spooler": {
        "name": "Fix Windows Print Spooler",
        "risk": RiskLevel.HIGH_ADMIN,
        "requires_admin": True,
        "service_type": "UAC_REQUIRED",
        "description": "Stops spooler service, purges locked PRINTERS queue files, and restarts service."
    },
    "generate_battery_report": {
        "name": "Battery Health & Degradation Report",
        "risk": RiskLevel.READ_ONLY,
        "requires_admin": False,
        "service_type": "NORMAL",
        "description": "Generates Windows powercfg battery report and calculates battery wear level."
    },
    "audit_domain_and_identity": {
        "name": "Domain & Entra ID Workstation Audit",
        "risk": RiskLevel.READ_ONLY,
        "requires_admin": False,
        "service_type": "NORMAL",
        "description": "Checks Active Directory domain join, secure channel trust, and Microsoft Entra ID status."
    },
    "audit_bitlocker": {
        "name": "BitLocker Drive Encryption Audit",
        "risk": RiskLevel.MEDIUM,
        "requires_admin": True,
        "service_type": "UAC_REQUIRED",
        "description": "Verifies BitLocker volume encryption percentage, cipher algorithm, and key protectors."
    },
    "generate_ticket_snippet": {
        "name": "Generate ITSM Support Ticket Snippet",
        "risk": RiskLevel.READ_ONLY,
        "requires_admin": False,
        "service_type": "NORMAL",
        "description": "Builds pre-formatted ticket template (Markdown/Jira/Text) with system telemetry."
    },
    "prepare_support_bundle": {
        "name": "Prepare IT Support Bundle",
        "risk": RiskLevel.READ_ONLY,
        "requires_admin": False,
        "service_type": "NORMAL",
        "description": "Generates a consolidated diagnostic report bundle."
    }
}


def is_admin() -> bool:
    """Checks whether the current process has Administrator privileges on Windows."""
    try:
        if sys.platform == "win32":
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        else:
            return os.geteuid() == 0  # type: ignore
    except Exception:
        return False


def is_task_allowed(task_id: str) -> bool:
    """Validates that the task is in the strict allowlist."""
    return task_id in TASK_ALLOWLIST


def get_task_metadata(task_id: str) -> Optional[Dict[str, Any]]:
    return TASK_ALLOWLIST.get(task_id)


def sanitize_hostname_or_ip(target: str) -> bool:
    """
    Validates that a hostname or IP address is strictly safe and contains no shell injection syntax.
    """
    if not target or len(target) > 255:
        return False
    # RFC 1123 hostname / IPv4 / IPv6 validation
    hostname_regex = r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])$"
    ipv4_regex = r"^(\d{1,3}\.){3}\d{1,3}$"
    ipv6_regex = r"^[a-fA-F0-9:]+$"

    target_clean = target.strip()
    return bool(
        re.match(hostname_regex, target_clean)
        or re.match(ipv4_regex, target_clean)
        or re.match(ipv6_regex, target_clean)
    )


def safe_subprocess_run(
    cmd_args: List[str],
    timeout_sec: int = 60,
    check_elevation: bool = False
) -> Tuple[int, str, str]:
    """
    Executes a process using safe arguments (never shell=True with user strings).
    Captures stdout, stderr, exit code, and handles timeouts gracefully.
    """
    if check_elevation and not is_admin():
        return (
            1,
            "",
            "Operation aborted: Administrator privileges are required to perform this action."
        )

    # Disallow empty commands
    if not cmd_args:
        return (1, "", "No command arguments provided.")

    try:
        # Hide console window on Windows if applicable
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW

        process = subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            creationflags=creationflags,
            encoding="utf-8",
            errors="replace"
        )

        stdout, stderr = process.communicate(timeout=timeout_sec)
        return (process.returncode, stdout, stderr)

    except subprocess.TimeoutExpired:
        process.kill()
        return (
            -1,
            "",
            f"Command timed out after {timeout_sec} seconds and was terminated safely."
        )
    except FileNotFoundError:
        return (
            127,
            "",
            f"Executable not found: {cmd_args[0]}"
        )
    except Exception as e:
        return (
            1,
            "",
            f"Execution error: {str(e)}"
        )


def elevate_process(args: Optional[List[str]] = None, exit_current: bool = False) -> bool:
    """
    Relaunches the application with elevated Administrator privileges via Windows UAC ('runas').
    If exit_current is True and elevation is launched successfully, exits the current process.
    """
    if sys.platform != "win32":
        return False

    if is_admin():
        return True  # Already elevated

    try:
        # Determine executable and parameters
        if getattr(sys, "frozen", False):
            # Running as bundled PyInstaller executable
            executable = sys.executable
            user_args = args if args is not None else sys.argv[1:]
            parameters = " ".join(f'"{a}"' for a in user_args)
        else:
            # Running as Python script
            executable = sys.executable
            script = os.path.abspath(sys.argv[0])
            user_args = args if args is not None else sys.argv[1:]
            param_list = [f'"{script}"'] + [f'"{a}"' for a in user_args]
            parameters = " ".join(param_list)

        # Trigger UAC elevation prompt
        hinstance = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            executable,
            parameters,
            os.getcwd(),
            1  # SW_SHOWNORMAL
        )

        # ShellExecute returns an HINSTANCE > 32 on success
        if int(hinstance) > 32:
            if exit_current:
                sys.exit(0)
            return True
        return False
    except Exception:
        return False


def get_privilege_and_account_details() -> Dict[str, Any]:
    """
    Retrieves detailed Windows privilege, UAC status, and local administrator membership.
    """
    details: Dict[str, Any] = {
        "is_admin": is_admin(),
        "uac_enabled": True,
        "consent_prompt_behavior": "Standard UAC Prompt",
        "local_admins": [],
        "session_elevation": "Elevated (Administrator)" if is_admin() else "Standard User (Non-Elevated)"
    }

    if sys.platform != "win32":
        return details

    # Inspect UAC system policy from registry
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
            0,
            winreg.KEY_READ
        )
        try:
            lua, _ = winreg.QueryValueEx(key, "EnableLUA")
            details["uac_enabled"] = bool(lua)
        except OSError:
            pass

        try:
            consent, _ = winreg.QueryValueEx(key, "ConsentPromptBehaviorAdmin")
            prompt_map = {
                0: "Elevate without prompting",
                1: "Prompt for credentials on secure desktop",
                2: "Prompt for consent on secure desktop",
                3: "Prompt for credentials",
                4: "Prompt for consent",
                5: "Prompt for consent for non-Windows binaries"
            }
            details["consent_prompt_behavior"] = prompt_map.get(consent, f"Level {consent}")
        except OSError:
            pass
        winreg.CloseKey(key)
    except Exception:
        pass

    # Enumerate Local Administrators group safely
    try:
        code, stdout, _ = safe_subprocess_run(["net", "localgroup", "administrators"], timeout_sec=5)
        if code == 0 and stdout:
            lines = stdout.splitlines()
            capture = False
            members = []
            for line in lines:
                stripped = line.strip()
                if "---" in stripped:
                    capture = True
                    continue
                if "The command completed" in stripped:
                    capture = False
                    break
                if capture and stripped:
                    members.append(stripped)
            details["local_admins"] = members
    except Exception:
        pass

    return details


