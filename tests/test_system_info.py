"""
Unit Tests for System Information Module
"""

from app.core.system_info import (
    get_windows_version_details,
    get_cpu_info,
    get_memory_info,
    get_disks_info,
    get_system_uptime,
    get_logged_in_user,
    collect_full_system_snapshot
)


def test_get_windows_version_details():
    details = get_windows_version_details()
    assert "os_name" in details
    assert "os_version" in details
    assert "os_build" in details
    assert len(details["architecture"]) > 0


def test_get_cpu_info():
    cpu = get_cpu_info()
    assert "model" in cpu
    assert cpu["cores_logical"] >= 1
    assert cpu["cores_physical"] >= 1
    assert isinstance(cpu["current_usage_percent"], (int, float))


def test_get_memory_info():
    mem = get_memory_info()
    assert mem["total_gb"] > 0
    assert mem["available_gb"] >= 0
    assert mem["used_gb"] >= 0
    assert 0 <= mem["percent_used"] <= 100


def test_get_disks_info():
    disks = get_disks_info()
    assert len(disks) >= 1
    for d in disks:
        assert d.total_gb > 0
        assert 0 <= d.percent_used <= 100
        assert len(d.mountpoint) > 0


def test_get_system_uptime():
    uptime = get_system_uptime()
    assert uptime["uptime_seconds"] >= 0
    assert uptime["uptime_hours"] >= 0
    assert "d" in uptime["formatted"]


def test_collect_full_system_snapshot():
    snap = collect_full_system_snapshot()
    assert len(snap.hostname) > 0
    assert snap.ram_total_gb > 0
    assert len(snap.disks) >= 1

