"""
Unit Tests for Inventory and Export Subsystem
"""

import os
import json
import tempfile
from app.core.inventory import (
    get_installed_applications,
    filter_applications,
    export_inventory_csv,
    export_inventory_json,
    export_inventory_html
)
from app.database.models import InstalledApp, SystemInventorySnapshot, DiskInfo


def test_get_installed_applications():
    apps = get_installed_applications()
    assert isinstance(apps, list)
    # Check that apps are non-empty or properly typed
    if apps:
        app = apps[0]
        assert hasattr(app, "name")
        assert hasattr(app, "version")
        assert hasattr(app, "publisher")


def test_filter_applications():
    sample = [
        InstalledApp(name="Microsoft Teams", version="1.0", publisher="Microsoft Corporation"),
        InstalledApp(name="Notepad++", version="8.5", publisher="Don Ho"),
        InstalledApp(name="Mozilla Firefox", version="118.0", publisher="Mozilla")
    ]

    filtered_teams = filter_applications(sample, "teams")
    assert len(filtered_teams) == 1
    assert filtered_teams[0].name == "Microsoft Teams"

    filtered_pub = filter_applications(sample, "mozilla")
    assert len(filtered_pub) == 1

    empty_filter = filter_applications(sample, "")
    assert len(empty_filter) == 3


def test_export_formats():
    snap = SystemInventorySnapshot(
        hostname="TEST-EXPORT",
        os_name="Windows 11",
        os_build="22631",
        cpu_model="Core i7",
        ram_total_gb=16.0,
        uptime_hours=12.0,
        logged_in_user="testuser",
        disks=[DiskInfo(device="C:", mountpoint="C:\\", fstype="NTFS", total_gb=256, used_gb=100, free_gb=156, percent_used=39.0)],
        installed_apps=[InstalledApp(name="TestApp", version="1.0", publisher="Tester Inc")]
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "inv.csv")
        export_inventory_csv(snap, csv_path)
        assert os.path.exists(csv_path)
        with open(csv_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "TEST-EXPORT" in content
            assert "TestApp" in content

        json_path = os.path.join(tmpdir, "inv.json")
        export_inventory_json(snap, json_path)
        assert os.path.exists(json_path)
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data["hostname"] == "TEST-EXPORT"
            assert len(data["installed_apps"]) == 1

        html_path = os.path.join(tmpdir, "inv.html")
        export_inventory_html(snap, html_path)
        assert os.path.exists(html_path)
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
            assert "TEST-EXPORT" in html
            assert "TestApp" in html

