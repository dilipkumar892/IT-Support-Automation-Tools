"""
Unit Tests for Database Layer
"""

import os
import tempfile
import pytest
from app.database.database import Database
from app.database.models import (
    SystemInventorySnapshot,
    DiskInfo,
    NetworkInterfaceInfo,
    InstalledApp,
    DiagnosticReport,
    AutomationHistoryEntry
)


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(db_path=path)
    yield db
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def test_schema_init(temp_db):
    assert os.path.exists(temp_db.db_path)


def test_inventory_snapshot_persistence(temp_db):
    snap = SystemInventorySnapshot(
        hostname="TEST-PC",
        os_name="Windows 11 Enterprise",
        os_version="23H2",
        os_build="22631.2861",
        architecture="AMD64",
        cpu_model="Intel Core i7-13700H",
        cpu_cores_logical=14,
        cpu_cores_physical=8,
        ram_total_gb=32.0,
        ram_available_gb=16.5,
        uptime_hours=24.5,
        logged_in_user="CORP\\testuser",
        is_admin=True,
        disks=[
            DiskInfo(device="C:", mountpoint="C:\\", fstype="NTFS", total_gb=500.0, used_gb=250.0, free_gb=250.0, percent_used=50.0)
        ],
        network_interfaces=[
            NetworkInterfaceInfo(name="Ethernet", mac_address="00:11:22:33:44:55", ipv4_addresses=["192.168.1.100"], is_up=True, speed_mbps=1000)
        ],
        installed_apps=[
            InstalledApp(name="Google Chrome", version="120.0", publisher="Google LLC", install_date="2024-01-10"),
            InstalledApp(name="7-Zip", version="23.01", publisher="Igor Pavlov", install_date="2023-11-05")
        ]
    )

    snap_id = temp_db.save_inventory_snapshot(snap)
    assert snap_id > 0

    latest = temp_db.get_latest_inventory_snapshot()
    assert latest is not None
    assert latest.hostname == "TEST-PC"
    assert latest.cpu_model == "Intel Core i7-13700H"
    assert len(latest.disks) == 1
    assert latest.disks[0].mountpoint == "C:\\"
    assert len(latest.installed_apps) == 2
    assert latest.installed_apps[0].name in ["Google Chrome", "7-Zip"]


def test_search_apps(temp_db):
    snap = SystemInventorySnapshot(
        hostname="TEST-SEARCH",
        installed_apps=[
            InstalledApp(name="Visual Studio Code", version="1.85", publisher="Microsoft Corporation"),
            InstalledApp(name="Slack", version="4.35", publisher="Slack Technologies")
        ]
    )
    temp_db.save_inventory_snapshot(snap)

    results = temp_db.search_apps("Visual")
    assert len(results) == 1
    assert results[0]["name"] == "Visual Studio Code"

    results_pub = temp_db.search_apps("Microsoft")
    assert len(results_pub) == 1


def test_diagnostic_report_lifecycle(temp_db):
    rep = DiagnosticReport(
        report_type="network",
        title="Network Check",
        status="PASS",
        summary="All systems nominal",
        findings=[{"item": "Gateway operational"}],
        recommendations=["Keep monitoring"],
        logs="Ping 1.1.1.1: 12ms"
    )
    rep_id = temp_db.save_diagnostic_report(rep)
    assert rep_id > 0

    reports = temp_db.get_recent_diagnostic_reports(limit=5)
    assert len(reports) >= 1
    assert reports[0].title == "Network Check"
    assert reports[0].status == "PASS"


def test_automation_history_lifecycle(temp_db):
    hist_id = temp_db.log_automation_start("sfc_verify_only", "SFC Integrity Check")
    assert hist_id > 0

    temp_db.update_automation_entry(
        entry_id=hist_id,
        status="SUCCESS",
        completed_at="2026-10-28T17:00:00",
        exit_code=0,
        output_text="Integrity check completed clean.",
        error_text=""
    )

    entries = temp_db.get_recent_automation_history(limit=5)
    assert len(entries) >= 1
    assert entries[0].task_name == "SFC Integrity Check"
    assert entries[0].status == "SUCCESS"
    assert entries[0].exit_code == 0

