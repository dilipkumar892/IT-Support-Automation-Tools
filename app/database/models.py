"""
Database Models and Dataclasses for IT Support Automation Suite
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class DiskInfo:
    device: str
    mountpoint: str
    fstype: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent_used: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NetworkInterfaceInfo:
    name: str
    mac_address: str
    ipv4_addresses: List[str] = field(default_factory=list)
    ipv6_addresses: List[str] = field(default_factory=list)
    is_up: bool = False
    speed_mbps: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InstalledApp:
    name: str
    version: str = "Unknown"
    publisher: str = "Unknown"
    install_date: str = "Unknown"
    install_location: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SystemInventorySnapshot:
    id: Optional[int] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    hostname: str = ""
    os_name: str = ""
    os_version: str = ""
    os_build: str = ""
    architecture: str = ""
    cpu_model: str = ""
    cpu_cores_logical: int = 0
    cpu_cores_physical: int = 0
    ram_total_gb: float = 0.0
    ram_available_gb: float = 0.0
    uptime_hours: float = 0.0
    logged_in_user: str = ""
    is_admin: bool = False
    disks: List[DiskInfo] = field(default_factory=list)
    network_interfaces: List[NetworkInterfaceInfo] = field(default_factory=list)
    installed_apps: List[InstalledApp] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class DiagnosticReport:
    id: Optional[int] = None
    report_type: str = "general"
    title: str = ""
    status: str = "PASS"  # PASS, WARNING, CRITICAL, INFO
    summary: str = ""
    findings: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    logs: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AutomationHistoryEntry:
    id: Optional[int] = None
    task_id: str = ""
    task_name: str = ""
    status: str = "PENDING"  # SUCCESS, FAILED, CANCELLED, RUNNING
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    exit_code: int = 0
    output_text: str = ""
    error_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

