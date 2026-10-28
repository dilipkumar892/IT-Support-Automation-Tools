"""
Unit Tests for Windows Troubleshooting & Diagnostics
"""

from unittest.mock import patch
from app.core.diagnostics import (
    analyze_disk_cleanup_targets,
    inspect_windows_services,
    inspect_startup_programs,
    get_top_resource_consumers,
    run_sfc_scan,
    run_dism_health,
    fix_print_spooler_service,
    reset_network_adapter_and_stack,
    reset_windows_update_agent,
    generate_battery_report,
    clean_junk_files,
    audit_domain_and_identity,
    audit_bitlocker_status,
    generate_itsm_ticket_payload
)


def test_analyze_disk_cleanup_targets():
    res = analyze_disk_cleanup_targets()
    assert "targets" in res
    assert "total_reclaimable_mb" in res
    assert res["total_reclaimable_mb"] >= 0


def test_inspect_windows_services():
    res = inspect_windows_services()
    assert "services" in res
    assert "wuauserv" in res["services"]


def test_inspect_startup_programs():
    apps = inspect_startup_programs()
    assert isinstance(apps, list)


def test_get_top_resource_consumers():
    res = get_top_resource_consumers()
    assert "top_cpu" in res
    assert "top_memory" in res
    assert len(res["top_cpu"]) > 0


def test_sfc_scan_non_admin_safety():
    with patch("app.core.diagnostics.is_admin", return_value=False):
        res = run_sfc_scan(repair_mode=False)
        assert res["success"] is False
        assert "Administrator privileges required" in res["message"]


def test_dism_health_non_admin_safety():
    with patch("app.core.diagnostics.is_admin", return_value=False):
        res = run_dism_health(operation="check")
        assert res["success"] is False
        assert "Administrator privileges required" in res["message"]


def test_sfc_scan_mocked_clean_output():
    with patch("app.core.diagnostics.is_admin", return_value=True):
        with patch("app.core.diagnostics.safe_subprocess_run", return_value=(0, "Windows Resource Protection did not find any integrity violations.", "")):
            res = run_sfc_scan(repair_mode=False)
            assert res["success"] is True
            assert "did not find any integrity violations" in res["summary"]


def test_fix_print_spooler_non_admin_safety():
    with patch("app.core.diagnostics.is_admin", return_value=False):
        res = fix_print_spooler_service()
        assert res["success"] is False
        assert "Administrator privileges required" in res["message"]


def test_reset_network_adapter_non_admin_safety():
    with patch("app.core.diagnostics.is_admin", return_value=False):
        res = reset_network_adapter_and_stack()
        assert res["success"] is False
        assert "Administrator privileges required" in res["message"]


def test_reset_windows_update_non_admin_safety():
    with patch("app.core.diagnostics.is_admin", return_value=False):
        res = reset_windows_update_agent()
        assert res["success"] is False
        assert "Administrator privileges required" in res["message"]


def test_generate_battery_report():
    # Normal user context
    res = generate_battery_report()
    assert "has_battery" in res
    assert "health_assessment" in res
    assert isinstance(res["battery_wear_percent"], (int, float))


def test_clean_junk_files_user_mode():
    # Normal user context
    res = clean_junk_files(system_level=False)
    assert res["success"] is True
    assert res["system_level"] is False
    assert res["reclaimed_mb"] >= 0.0


def test_audit_domain_and_identity():
    # Normal user context
    res = audit_domain_and_identity()
    assert "domain_joined" in res
    assert "azure_ad_joined" in res
    assert "domain_name" in res


def test_audit_bitlocker_non_admin_safety():
    with patch("app.core.diagnostics.is_admin", return_value=False):
        res = audit_bitlocker_status()
        assert res["success"] is False
        assert "Administrator privileges required" in res["message"]


def test_generate_itsm_ticket_payload():
    # Normal user context
    payload = generate_itsm_ticket_payload()
    assert "markdown" in payload
    assert "jira" in payload
    assert "plain" in payload
    assert "IT Support" in payload["markdown"]
    assert "Operating System" in payload["markdown"]

