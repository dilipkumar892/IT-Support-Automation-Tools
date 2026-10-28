"""
Unit Tests for Safety and Security Subsystem
"""

import pytest
from app.core.safety import (
    is_admin,
    is_task_allowed,
    sanitize_hostname_or_ip,
    safe_subprocess_run,
    get_task_metadata,
    elevate_process,
    get_privilege_and_account_details,
    RiskLevel
)


def test_sanitize_hostname_or_ip_valid():
    assert sanitize_hostname_or_ip("google.com") is True
    assert sanitize_hostname_or_ip("192.168.1.1") is True
    assert sanitize_hostname_or_ip("10.0.0.254") is True
    assert sanitize_hostname_or_ip("sub.domain.corp.local") is True
    assert sanitize_hostname_or_ip("fe80::1") is True


def test_sanitize_hostname_or_ip_malicious_rejection():
    # Command injection and unsafe inputs must be rejected
    assert sanitize_hostname_or_ip("google.com; rm -rf /") is False
    assert sanitize_hostname_or_ip("192.168.1.1 & calc.exe") is False
    assert sanitize_hostname_or_ip("8.8.8.8 | powershell") is False
    assert sanitize_hostname_or_ip("`whoami`") is False
    assert sanitize_hostname_or_ip("$env:USERNAME") is False
    assert sanitize_hostname_or_ip("") is False
    assert sanitize_hostname_or_ip("   ") is False


def test_task_allowlist_validation():
    assert is_task_allowed("collect_system_info") is True
    assert is_task_allowed("run_network_diagnostics") is True
    assert is_task_allowed("sfc_verify_only") is True
    assert is_task_allowed("flush_dns_cache") is True
    assert is_task_allowed("prepare_support_bundle") is True

    # Arbitrary tasks must be strictly disallowed
    assert is_task_allowed("arbitrary_command") is False
    assert is_task_allowed("download_execute") is False
    assert is_task_allowed("format_drive") is False


def test_task_metadata():
    meta = get_task_metadata("collect_system_info")
    assert meta is not None
    assert meta["risk"] == RiskLevel.READ_ONLY
    assert meta["requires_admin"] is False

    sfc_meta = get_task_metadata("sfc_repair")
    assert sfc_meta is not None
    assert sfc_meta["risk"] == RiskLevel.HIGH_ADMIN
    assert sfc_meta["requires_admin"] is True


def test_safe_subprocess_run():
    # Safe echo or python test
    code, stdout, stderr = safe_subprocess_run(["python", "-c", "print('hello_safe')"], timeout_sec=5)
    assert code == 0
    assert "hello_safe" in stdout


def test_safe_subprocess_timeout():
    # Should safely timeout and terminate without hanging
    code, stdout, stderr = safe_subprocess_run(
        ["python", "-c", "import time; time.sleep(10)"],
        timeout_sec=1
    )
    assert code == -1
    assert "timed out" in stderr.lower()


def test_get_privilege_and_account_details():
    privs = get_privilege_and_account_details()
    assert "is_admin" in privs
    assert "session_elevation" in privs
    assert "uac_enabled" in privs
    assert isinstance(privs["local_admins"], list)


def test_elevate_process_mock_already_admin():
    from unittest.mock import patch
    with patch("app.core.safety.is_admin", return_value=True):
        # When already admin, returns True immediately without spawning
        assert elevate_process() is True

