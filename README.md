# Professional IT Support Automation Suite

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PySide6%20(Qt6)-41CD52?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6?logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![Tests](https://img.shields.io/badge/Tests-51%20Passed-10b981)](tests/)
[![Security](https://img.shields.io/badge/Security-Least--Privilege%20%26%20Allowlisted-00d2ff)](#11-security-review)

A modular desktop application engineered for Desktop Support Engineers, Windows System Administrators, and IT Operations teams. It automates repetitive diagnostic and maintenance workflows safely, transparently, and with strict guardrails against arbitrary execution.

---

## 1. Key Capabilities

* **Dual-Mode Permission Architecture (Normal vs. UAC Required):** Non-destructive read tasks operate seamlessly in standard user context, while administrative repairs (SFC repair, DISM restore, Print Spooler purge, Winsock reset, BitLocker audit) feature one-click UAC promotion.
* **Real-Time System Telemetry Dashboard:** Live monitoring of CPU utilization, RAM usage, storage volume capacities, network latency, Windows Update services, and system uptime.
* **Hardware & IT Asset Inventory:** Enumeration of physical/logical processors, memory DIMMs, storage volumes, network MAC/IP addresses, and comprehensive Windows Registry software inventory (32-bit and 64-bit).
* **Automated Network Diagnostics & Stack Reset:** Gateway reachability checks, multi-target DNS resolution tests, ICMP ping latency measurements, HTTP/HTTPS connectivity verification, one-click DNS resolver cache flushing, and full Winsock/TCP stack resets.
* **Print Spooler Repair Doctor (UAC):** Automatically stops the spooler service, purges locked `.SPL` and `.SHD` job files from `C:\Windows\System32\spool\PRINTERS`, and restarts the service.
* **Windows Update Component Doctor (UAC):** Stops update services (`wuauserv`, `bits`, `cryptsvc`), purges corrupted `SoftwareDistribution\Download` cache, and restarts services.
* **Laptop Battery Health & Degradation Reporter:** Uses Windows `powercfg /batteryreport` to calculate Design vs. Full Charge capacity and compute real battery wear level % without elevation.
* **Active Directory & Microsoft Entra ID (Azure AD) Workstation Doctor:** Evaluates domain join state, secure channel trust, and Microsoft Entra ID registration via `dsregcmd /status`.
* **BitLocker Drive Encryption Auditor (UAC):** Inspects volume protection status, cipher algorithms, and key protector configuration via `manage-bde`.
* **Safe Junk & Disk Cleanup:** Dual-mode cleanup purging `%TEMP%` in user mode and system-level `C:\Windows\Temp` + WER queues under UAC elevation.
* **One-Click ITSM Ticket Generator:** Generates formatted Markdown, Jira, and Plain-Text support ticket summaries ready to copy to clipboard for ServiceNow, Jira Service Management, or Zendesk.
* **Multi-Format Support Reporting:** One-click export of diagnostic findings, system specs, detected problems, and remediation actions into **HTML**, **PDF** (native Qt print rendering), **CSV**, and **JSON**.

---

## 2. Architecture & Folder Structure

```
IT-Support-Automation/
├── main.py                          # Application entry point (GUI & Headless CLI)
├── it_support.spec                  # PyInstaller build specification
├── requirements.txt                 # Dependencies
├── README.md                        # Documentation & Engineering Guide
├── LICENSE                          # MIT License
├── .gitignore                       # Git exclusions
├── config/
│   └── settings.json                # JSON configuration & task allowlist
├── app/
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py           # Master navigation & theme container
│   │   ├── dashboard.py             # Telemetry dashboard & quick action cards
│   │   ├── inventory_view.py        # Asset inventory table, search & export
│   │   ├── diagnostics_view.py      # SFC, DISM, Event Log & Services tabs
│   │   ├── automation_view.py       # Threaded task orchestrator & history
│   │   └── settings_view.py         # Guardrails, timeouts & paths
│   ├── core/
│   │   ├── __init__.py
│   │   ├── system_info.py           # Real Windows hardware & OS collector
│   │   ├── network.py               # Gateway, ping, DNS, HTTP diagnostics
│   │   ├── inventory.py             # Registry software scanner & exporters
│   │   ├── diagnostics.py           # SFC, DISM, disk analysis & event logs
│   │   ├── automation.py            # Async task runner with cancellation tokens
│   │   ├── logging.py               # Rotating file & in-memory GUI log stream
│   │   └── safety.py                # Privilege checks, sanitizer, allowlists
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py                # Dataclasses & SQLite schema mappings
│   │   └── database.py              # SQLite connection pooling & CRUD
│   └── reports/
│       ├── __init__.py
│       ├── html_report.py           # Standalone responsive HTML & CSV generator
│       └── pdf_report.py            # Native PySide6 vector PDF generator
├── scripts/
│   ├── system_diagnostics.ps1       # Structured PowerShell system telemetry
│   ├── network_diagnostics.ps1      # Structured PowerShell network probe
│   └── windows_updates.ps1          # Structured PowerShell hotfix & WU audit
├── tests/
│   ├── __init__.py
│   ├── test_safety.py               # Injection defense & permission tests
│   ├── test_database.py             # SQLite persistence & query tests
│   ├── test_system_info.py          # Real hardware telemetry tests
│   ├── test_network.py              # DNS, ping & socket connection tests
│   ├── test_inventory.py            # Software scan & export format tests
│   ├── test_diagnostics.py          # Troubleshooting & disk analysis tests
│   ├── test_automation.py           # Threaded execution & cancellation tests
│   ├── test_reports.py              # HTML, CSV, JSON & PDF export tests
│   └── test_gui.py                  # Headless PySide6 window lifecycle tests
└── assets/                          # Icons and visual assets
```

---

## 3. Technology Stack

* **Python 3.10+**: Core programming language.
* **PySide6 (Qt 6.12)**: Modern GPU-accelerated desktop interface with custom dark neon stylesheet.
* **PowerShell**: Integration scripts using CIM/WMI cmdlets with JSON output formatting.
* **SQLite 3**: Zero-configuration, ACID-compliant local database storing snapshots, diagnostic reports, and task run histories.
* **Native Qt PDF & HTML**: Pixel-perfect reporting without external headless browser dependencies.
* **pytest**: 41 comprehensive unit and integration tests with mock isolation.
* **PyInstaller**: Standalone Windows binary packaging with UAC elevation support.

---

## 4. Installation Instructions

### Prerequisites
* Windows 10 or Windows 11 (64-bit recommended)
* Python 3.10 or later

### Step 1: Clone or Navigate to the Repository
```powershell
cd "c:\Users\Dilip\Documents\Projects\IT Support Automation Tools"
```

### Step 2: Create and Activate a Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

---

## 5. How to Run the Application

### Launch the Desktop GUI
To launch the full interactive desktop interface:
```powershell
python main.py
```
> **Tip:** To execute privileged diagnostic tools (such as SFC Repair or DISM Component Store Restore), launch PowerShell or the application as **Administrator**. The application dynamically detects session privileges and displays an elevation status badge in the sidebar.

### Headless CLI Mode (Automation & Scripting)
The suite can run entirely from the command line without launching the GUI.

* **List all supported tasks in the security allowlist:**
  ```powershell
  python main.py --list-tasks
  ```

* **Run a specific automation task:**
  ```powershell
  python main.py --task collect_system_info
  python main.py --task run_network_diagnostics
  python main.py --task prepare_support_bundle
  python main.py --task flush_dns_cache
  ```

---

## 6. Database Initialization & Schema

The application initializes an SQLite database automatically on first launch at `data/it_support.db`.

### Key Tables
1. **`inventory_snapshots`**: Captures hardware and OS configuration snapshots (Hostname, OS, CPU model, RAM, Uptime, User).
2. **`inventory_disks`**: Volume mountpoints, capacity, free space, and usage percentages.
3. **`inventory_networks`**: Adapter names, MAC addresses, IPv4/IPv6 allocations, and link speeds.
4. **`inventory_apps`**: Application names, versions, publishers, and installation dates extracted from the 32-bit and 64-bit Windows Registry uninstall trees.
5. **`diagnostic_reports`**: Consolidated report records containing finding items, remediation steps, and log traces.
6. **`automation_history`**: Audit trail of every automated task execution, including start/end timestamps, exit codes, output traces, and error messages.

---

## 7. Testing Guide

The suite includes 41 automated unit and integration tests validating safety mechanisms, database CRUD operations, real hardware extraction, network diagnostics, report exports, and GUI instantiation.

### Run All Tests
```powershell
pytest -v
```

### Run Specific Test Modules
```powershell
# Security and validation tests
pytest tests/test_safety.py -v

# Database persistence tests
pytest tests/test_database.py -v

# Network diagnostic tests
pytest tests/test_network.py -v

# Automation engine and cancellation tests
pytest tests/test_automation.py -v

# Headless GUI startup tests
pytest tests/test_gui.py -v
```

---

## 8. PyInstaller Packaging Instructions

You can bundle the suite into a standalone Windows executable that Desktop Support Engineers can run without installing Python.

### Build Executable Directory
```powershell
pyinstaller it_support.spec --clean -y
```

The compiled application and all its required assets will be placed in `dist/ITSupportSuite/`.

### Run the Packaged Binary
```powershell
.\dist\ITSupportSuite\ITSupportSuite.exe
```

### Single-File Portable Build (Alternative)
To create a single portable `.exe`:
```powershell
pyinstaller --onefile --windowed --name "ITSupportSuite" `
  --add-data "config/settings.json;config" `
  --add-data "scripts/*.ps1;scripts" `
  main.py
```

---

## 9. Ponytail Code Review Guidelines

In accordance with minimal engineering and Ponytail principles:
* **Standard Library First:** The application relies on Python standard libraries (`socket`, `platform`, `urllib`, `sqlite3`, `csv`, `json`, `winreg`, `ctypes`, `subprocess`) wherever possible, avoiding unnecessary third-party abstractions.
* **Native Qt PDF Rendering:** PDF reports are rendered directly using PySide6's built-in `QTextDocument` and `QPdfWriter`, eliminating the need for heavyweight tools like wkhtmltopdf or Chromium headless binaries.
* **Controlled Subprocess Wrapper:** `app/core/safety.py` wraps `subprocess.Popen` in list-argument format without invoking `shell=True` with unescaped strings, preventing command-injection attacks while keeping code concise.
* **No Speculative Abstractions:** All data models are lightweight standard Python `dataclasses` with straightforward database schema mapping.

---

## 10. Security Review & Guardrails

The application follows defense-in-depth principles:

1. **Least-Privilege Execution:** Non-destructive read tasks (hardware inventory, network ping, DNS check, event log queries) execute without requiring administrative rights.
2. **Elevation Enforcement:** Destructive or repair tasks (`sfc_repair`, `dism_restore_health`, `flush_dns_cache`) strictly check for administrator privileges before attempting execution.
3. **Explicit User Confirmation:** High-impact operations present modal confirmation dialogues explaining what changes will be applied before any command is dispatched.
4. **Strict Task Allowlist:** The automation engine accepts only registered task identifiers defined in `TASK_ALLOWLIST`. Arbitrary commands and scripts are categorically rejected.
5. **No Shell Injections:** Network diagnostic targets (hostnames, IP addresses) are validated against strict RFC 1123 and IPv4/IPv6 regex patterns.
6. **Data Privacy:** The software inventory scanner enumerates application metadata from Windows Registry uninstall keys only. **It never inspects user documents, downloads, browser histories, cookies, or saved credentials.**
7. **No External Data Exfiltration:** All reports and database records remain strictly on local storage (`data/` and `reports_export/`).

---

## 11. Future Roadmap

- [ ] **Integration with Active Directory / Entra ID:** Automated retrieval of domain computer membership and BitLocker recovery key status.
- [ ] **ITSM Ticket Webhook Connectors:** Direct export of diagnostic bundles into ServiceNow, Jira Service Management, or Zendesk via REST API.
- [ ] **Windows Event Log AI Summarizer:** Local NLP classification of repeated event log patterns to highlight root causes.
- [ ] **Automated Driver & Firmware Audit:** Querying HP, Dell, and Lenovo enterprise update catalogs to identify outdated BIOS and device drivers.

---

## 12. License

Distributed under the [MIT License](LICENSE).

