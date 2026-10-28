"""
System Information Collector
Gathers genuine hardware, OS, disk, memory, CPU, and user metrics on Windows.
"""

import os
import sys
import socket
import platform
import time
from datetime import datetime
from typing import Dict, Any, List

import psutil

from .safety import is_admin
from ..database.models import (
    SystemInventorySnapshot,
    DiskInfo,
    NetworkInterfaceInfo
)


def get_windows_version_details() -> Dict[str, str]:
    """Retrieves detailed Windows release name and build number."""
    os_name = f"Windows {platform.release()}"
    os_version = platform.version()
    os_build = ""

    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
            )
            product_name, _ = winreg.QueryValueEx(key, "ProductName")
            display_version, _ = winreg.QueryValueEx(key, "DisplayVersion")
            current_build, _ = winreg.QueryValueEx(key, "CurrentBuild")
            ubr, _ = winreg.QueryValueEx(key, "UBR")
            winreg.CloseKey(key)

            os_name = str(product_name)
            os_version = str(display_version)
            os_build = f"{current_build}.{ubr}"
        except Exception:
            # Fallback to standard platform
            parts = platform.version().split(".")
            os_build = parts[-1] if parts else platform.version()

    return {
        "os_name": os_name,
        "os_version": os_version,
        "os_build": os_build,
        "architecture": platform.machine()
    }


def get_cpu_info() -> Dict[str, Any]:
    """Retrieves CPU processor model and core counts."""
    cpu_model = platform.processor() or "Unknown CPU"

    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            )
            processor_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            cpu_model = processor_name.strip()
        except Exception:
            pass

    cores_physical = psutil.cpu_count(logical=False) or 1
    cores_logical = psutil.cpu_count(logical=True) or 1
    cpu_percent = psutil.cpu_percent(interval=None)

    return {
        "model": cpu_model,
        "cores_physical": cores_physical,
        "cores_logical": cores_logical,
        "current_usage_percent": cpu_percent
    }


def get_memory_info() -> Dict[str, Any]:
    """Retrieves RAM metrics."""
    vmem = psutil.virtual_memory()
    total_gb = round(vmem.total / (1024 ** 3), 2)
    available_gb = round(vmem.available / (1024 ** 3), 2)
    used_gb = round((vmem.total - vmem.available) / (1024 ** 3), 2)
    percent = vmem.percent

    return {
        "total_gb": total_gb,
        "available_gb": available_gb,
        "used_gb": used_gb,
        "percent_used": percent
    }


def get_disks_info() -> List[DiskInfo]:
    """Retrieves all mounted storage partitions and their capacity."""
    disks: List[DiskInfo] = []
    partitions = psutil.disk_partitions(all=False)

    for part in partitions:
        try:
            # Skip optical or inaccessible drives
            if "cdrom" in part.opts or part.fstype == "":
                continue

            usage = psutil.disk_usage(part.mountpoint)
            total_gb = round(usage.total / (1024 ** 3), 2)
            used_gb = round(usage.used / (1024 ** 3), 2)
            free_gb = round(usage.free / (1024 ** 3), 2)

            disks.append(DiskInfo(
                device=part.device,
                mountpoint=part.mountpoint,
                fstype=part.fstype,
                total_gb=total_gb,
                used_gb=used_gb,
                free_gb=free_gb,
                percent_used=usage.percent
            ))
        except (PermissionError, FileNotFoundError, OSError):
            continue

    return disks


def get_network_interfaces() -> List[NetworkInterfaceInfo]:
    """Retrieves active and inactive network adapters, IP addresses, and MACs."""
    interfaces: List[NetworkInterfaceInfo] = []
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()

    for name, addr_list in addrs.items():
        mac = ""
        ipv4 = []
        ipv6 = []

        for addr in addr_list:
            if addr.family == psutil.AF_LINK or (hasattr(socket, "AF_LINK") and addr.family == socket.AF_LINK):
                mac = addr.address
            elif addr.family == socket.AF_INET:
                ipv4.append(addr.address)
            elif addr.family == socket.AF_INET6:
                ipv6.append(addr.address.split("%")[0])  # remove scope id if present

        stat = stats.get(name)
        is_up = stat.isup if stat else False
        speed = stat.speed if stat else 0

        # Filter out empty loopback/virtual adapters with no IP or MAC if needed
        interfaces.append(NetworkInterfaceInfo(
            name=name,
            mac_address=mac,
            ipv4_addresses=ipv4,
            ipv6_addresses=ipv6,
            is_up=is_up,
            speed_mbps=speed
        ))

    return interfaces


def get_system_uptime() -> Dict[str, Any]:
    """Retrieves boot time and formatted uptime."""
    boot_time = psutil.boot_time()
    now = time.time()
    uptime_seconds = max(0, int(now - boot_time))
    uptime_hours = round(uptime_seconds / 3600.0, 2)

    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    formatted = f"{days}d {hours}h {minutes}m"

    return {
        "boot_time_iso": datetime.fromtimestamp(boot_time).isoformat(),
        "uptime_seconds": uptime_seconds,
        "uptime_hours": uptime_hours,
        "formatted": formatted
    }


def get_logged_in_user() -> str:
    """Returns DOMAIN\\Username or username."""
    try:
        user = os.getlogin()
    except Exception:
        user = os.environ.get("USERNAME", "Unknown")
    domain = os.environ.get("USERDOMAIN", "")
    if domain and domain != user:
        return f"{domain}\\{user}"
    return user


def collect_full_system_snapshot() -> SystemInventorySnapshot:
    """Consolidates complete system metrics into a SystemInventorySnapshot dataclass."""
    hostname = socket.gethostname()
    os_info = get_windows_version_details()
    cpu_info = get_cpu_info()
    mem_info = get_memory_info()
    disks = get_disks_info()
    networks = get_network_interfaces()
    uptime_info = get_system_uptime()
    user = get_logged_in_user()
    admin_status = is_admin()

    return SystemInventorySnapshot(
        timestamp=datetime.now().isoformat(),
        hostname=hostname,
        os_name=os_info["os_name"],
        os_version=os_info["os_version"],
        os_build=os_info["os_build"],
        architecture=os_info["architecture"],
        cpu_model=cpu_info["model"],
        cpu_cores_logical=cpu_info["cores_logical"],
        cpu_cores_physical=cpu_info["cores_physical"],
        ram_total_gb=mem_info["total_gb"],
        ram_available_gb=mem_info["available_gb"],
        uptime_hours=uptime_info["uptime_hours"],
        logged_in_user=user,
        is_admin=admin_status,
        disks=disks,
        network_interfaces=networks,
        installed_apps=[]
    )

