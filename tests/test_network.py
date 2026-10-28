"""
Unit Tests for Network Diagnostics Subsystem
"""

from app.core.network import (
    test_dns_resolution as execute_dns_check,
    ping_host as execute_ping,
    test_tcp_port as execute_tcp_port,
    test_http_connectivity as execute_http_check,
    run_comprehensive_network_diagnostics as execute_comprehensive_net_diag
)


def test_dns_resolution_real():
    res = execute_dns_check(["google.com"])
    assert res["status"] in ["OK", "DEGRADED", "FAIL"]
    assert "google.com" in res["details"]
    if res["status"] == "OK":
        assert len(res["details"]["google.com"]["ips"]) > 0


def test_ping_host_safe_validation():
    # Attempting injection into ping
    res = execute_ping("8.8.8.8 & echo test")
    assert res["success"] is False
    assert "Invalid or unsafe" in res["error"]


def test_ping_localhost():
    res = execute_ping("127.0.0.1", count=2, timeout_sec=2)
    assert res["host"] == "127.0.0.1"
    assert res["packets_sent"] == 2
    assert res["success"] is True
    assert res["packet_loss_percent"] == 0.0


def test_tcp_port_loopback():
    # Test checking closed port
    res = execute_tcp_port("127.0.0.1", 65432, timeout_sec=0.5)
    assert res["host"] == "127.0.0.1"
    assert res["port"] == 65432
    assert res["success"] is False


def test_http_connectivity_real():
    res = execute_http_check("https://www.google.com", timeout_sec=3)
    assert isinstance(res["success"], bool)


def test_run_comprehensive_network_diagnostics():
    diag = execute_comprehensive_net_diag()
    assert diag["status"] in ["PASS", "WARNING", "CRITICAL"]
    assert len(diag["findings"]) > 0
    assert "timestamp" in diag
