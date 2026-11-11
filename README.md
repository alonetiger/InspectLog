<div align="center">

# 🔍 Inspect Log

**Professional Hardware Genuineness, Component Health, & Anti-Fraud Verification Suite for Windows**

<br>

<p align="center">
  <a href="https://github.com/alonetiger/InspectLog/releases/latest/download/InspectLog.exe">
    <img src="https://img.shields.io/badge/⬇️%20DOWNLOAD%20NOW-InspectLog.exe%20(Windows%2010%20%2F%2011)-0284C7?style=for-the-badge&logo=windows&logoColor=white" height="46" alt="Download InspectLog.exe" />
  </a>
  &nbsp;&nbsp;
  <a href="https://github.com/alonetiger/InspectLog/releases">
    <img src="https://img.shields.io/badge/📦%20ALL%20RELEASES-v1.0.0-2563EB?style=for-the-badge&logo=github&logoColor=white" height="46" alt="All Releases" />
  </a>
</p>

<p align="center">
  <b>⚡ Single-file portable executable • Zero installation required • Just download and run!</b>
</p>

<br>

[![Platform: Windows 10 / 11](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D4?logo=windows)](https://microsoft.com/windows)
[![Release: v1.0.0](https://img.shields.io/badge/Release-v1.0.0-success?logo=github)](https://github.com/alonetiger/InspectLog/releases/tag/v1.0.0)
[![Python: 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://python.org)
[![GUI: PySide6 (Qt6)](https://img.shields.io/badge/GUI-PySide6%20%28Qt6%29-41CD52?logo=qt)](https://qt.io)
[![Test Suite: 68 Passing](https://img.shields.io/badge/Tests-68%20Passed-brightgreen?logo=pytest)](https://pytest.org)
[![Admin: Required](https://img.shields.io/badge/UAC-Administrator-critical)](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/user-account-control/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

</div>

---

## 📥 Direct Download & Quick Start

You do **not** need Python or any development tools to use Inspect Log. Anyone can download and run the standalone software directly:

| Download Link | Description | Size | Platform |
| :--- | :--- | :--- | :--- |
| [**⬇️ Download InspectLog.exe**](https://github.com/alonetiger/InspectLog/releases/latest/download/InspectLog.exe) | Single Portable Windows Executable (Official Release) | 75.6 MB | Windows 10 / 11 (64-bit) |
| [**📦 GitHub Releases Page**](https://github.com/alonetiger/InspectLog/releases) | View all release notes, assets, and SHA-256 checksums | — | — |

### How to Run:
1. **Download**: Click the [**Download InspectLog.exe**](https://github.com/alonetiger/InspectLog/releases/latest/download/InspectLog.exe) button above.
2. **Launch**: Double-click `InspectLog.exe` on your PC.
3. **Admin Prompt**: Click **Yes** when Windows User Account Control (UAC) prompts for Administrator permissions (required to query low-level drive SMART data and ACPI sensors).
4. **Inspect**: Click the primary **`🔍 Check PC`** button on the home screen.
5. **View In-App Report**: Within ~10-15 seconds, your complete hardware authenticity & health report appears directly inside the software dashboard!

---

## 📌 Overview

**Inspect Log** is an advanced desktop diagnostic application built for buyers, technicians, and system builders evaluating new or second-hand PCs and laptops. 

When buying pre-owned or refurbished computers, counterfeit components, altered BIOS strings, spoofed CPU model names, worn-out batteries, failing SSDs with reset SMART data, and counterfeit flash storage drives are common risks. **Inspect Log** runs deep diagnostic readers, benchmarks, and interactive hardware checks to cross-validate every critical specification against independent low-level hardware sources, detecting fraud and component degradation before money changes hands.

---

## ⚖️ Core Engineering Principle: Accuracy Over Looks

- **Zero Fake Data**: The application never displays invented, default, estimated, or placeholder values. If a sensor or metric cannot be accessed (due to driver limits, virtualization, or permission constraints), it displays **"Unavailable"** alongside the exact technical reason.
- **Dual-Source Cross-Validation**: Every critical metric is verified across $\ge 2$ independent low-level sources (e.g., WMI Win32_Processor vs. CPUID machine registers vs. py-cpuinfo; WMI Win32_DiskDrive vs. vendor-level ATA/NVMe SMART via bundled `smartctl`).
- **Complete Provenance**: Every metric displays its origin data source (e.g., `WMI`, `SMART`, `powercfg`, `NVML`, `netsh`) and an algorithmic confidence score:
  - 🟢 **High**: Multiple independent sources concur within tight tolerances.
  - 🟡 **Medium**: Single authoritative hardware source verified.
  - 🔴 **Low**: Discrepancy detected between independent sources (potential spoofing or hardware fault).

---

## 🚀 Key Modules & Diagnostic Checks

### 1. 🖥️ System Identity & Anti-Tamper
- Reads Manufacturer, Model, System Serial Number, Motherboard Model, and BIOS Version/Release Date.
- **Anti-Fraud Filter**: Flags generic factory placeholders (`"To be filled by O.E.M."`, `"System Serial Number"`, `"Default String"`).
- Cross-references BIOS release date against processor generation to identify flashed/mismatched BIOS configurations.
- Audits Windows Genuine activation status via `SoftwareLicensingProduct`.

### 2. 🔋 Battery Health & Degradation (Laptops)
- Analyzes Manufacturer, Chemistry, Cycle Count, Factory Design Capacity (mWh), and Current Full-Charge Capacity (mWh).
- **Wear Percentage Calculation**: $\text{Wear} = \left(1 - \frac{\text{Full Charge Capacity}}{\text{Design Capacity}}\right) \times 100$.
- **Automated Health Verdict**:
  - `Excellent`: $< 10\%$ wear
  - `Good`: $10\% - 25\%$ wear
  - `Fair`: $25\% - 40\%$ wear
  - `Replace / Negotiate`: $> 40\%$ wear
- **60-Second Real-Time Discharge Test**: Samples battery discharge rate every second under controlled load to catch sudden voltage drops indicative of damaged cells.
- **Graceful Desktop Mode**: Intelligently detects AC-only desktop systems, excludes battery tests from scoring, and redistributes weight proportionally across active hardware.

### 3. 💾 Storage Integrity & Fake Capacity Test
- Detects all connected NVMe and SATA drives via direct WMI and bundled `smartctl.exe` v7.5.
- Audits critical SMART metrics: Power-On Hours (POH), Power Cycles, Reallocated/Pending Bad Sectors, Temperature, Percentage Used, and Total Bytes Written (TBW).
- **Non-Destructive Fake-Capacity Verification**: Writes cryptographically indexed 1 MB blocks across the address space within a safe temporary sandbox (never touching user data), verifies block headers, and immediately cleans up. Detects fake USB drives and counterfeit SSDs with hacked firmware loopbacks.
- **Drive Performance Benchmark**: Measures sequential and 4K random read/write speeds.

### 4. 🧠 RAM Authenticity & Bit-Pattern Stress
- Enumerates each physical memory slot: Capacity, Configured Speed vs. Rated Speed, Form Factor, Memory Type (DDR4, DDR5, LPDDR), and Manufacturer.
- Calculates and verifies Single vs. Dual/Quad Channel topology.
- Flags downclocked RAM running below XMP/EXPO rated speeds.
- **Built-in Memory Pattern Test**: Executes walking-ones and pseudo-random bit pattern stress tests on configurable blocks of free RAM with real-time progress and hardware error counters.

### 5. ⚡ CPU Spoofing Detector & Thermal Throttling
- Extracts Vendor, Genuine Model, Architecture, Core Count, Logical Thread Count, Base/Max Clock, and Cache sizes.
- **Hardware Spoofing Detection Engine**: Compares the reported CPU string against physical core counts, thread topology, and L3 cache size in an internal reference database to detect renamed low-end processors (e.g., Celeron relabeled as Core i9).
- **Stress Test & Thermal Throttling Verdict**: Stresses all cores using multi-threaded numerical operations while monitoring clock frequency drops ($> 10\%$) and temperature thresholds ($95^\circ\text{C}$ emergency ceiling).

### 6. 🎮 GPU Authenticity & VRAM Validation
- Distinguishes between Integrated (iGPU) and Dedicated (dGPU) adapters.
- Evaluates GPU Model, Driver Version, PCI Vendor ID, and verifies real physical VRAM via 64-bit registry and NVIDIA NVML telemetry.
- Runs OpenGL/DirectX stress workload while monitoring artifacts, temperature curves, and driver crashes.

### 7. 🖥️ Display Diagnostics & Pixel Audit
- Reads active desktop resolution, refresh rate (Hz), DPI scaling, and hardware panel physical size via WMI EDID binary parsing.
- Flags mismatches between active resolution and native panel resolution.
- **Full-Screen Interactive Pixel Test**: Full-screen test sequence cycling solid colors (Red, Green, Blue, White, Black, 50% Grey) for dead/stuck pixel detection, gradient banding, and backlight bleed inspection.

### 8. 🎮 Interactive Input & I/O Diagnostics
- **Interactive Keyboard Map**: On-screen keyboard graphic that illuminates keys in real-time as they are pressed.
- **Touchpad & Mouse Tester**: Visual canvas for left/right/middle click tracking, double-click timing, scroll wheel delta, and cursor gesture tracing.
- **Webcam Video Preview**: Real-time camera preview test verifying resolution and FPS.
- **Microphone Audio Meter**: Live decibel VU meter monitoring ambient input levels.
- **Stereo Audio Speaker Test**: Independent left-channel and right-channel sine wave tone playback (440 Hz / 880 Hz).
- **USB Port Insertion Monitor**: Guides user through inserting a thumb drive into each physical port, logging device IDs as verified.

### 9. 🌡️ Thermals & Fans Sensor Monitor
- Gathers ACPI thermal zone temperatures, fan RPM sensors, and motherboard core voltages via WMI and hardware monitoring providers.
- Flags overheating idle components ($> 85^\circ\text{C}$).

### 10. 🔒 Security, Locks & Enterprise Enrollment
- **UEFI Secure Boot Status**: Audits whether Secure Boot is enabled.
- **TPM Security**: Confirms presence and activation of TPM 2.0.
- **Enterprise MDM Enrollment Check**: Queries registry enrollment providers (Intune, AirWatch, MobileIron) to warn buyers if the laptop is bound to a corporate Mobile Device Management system.
- **Domain Join Check**: Flags devices bound to active corporate Active Directory or Azure AD domains.

---

## 🏗️ Architecture & Clean Code

Inspect Log is architected according to strict separation of concerns:

```
InspectLog/
├── inspectlog/
│   ├── core/                      # Hardware Abstraction Layer (HAL)
│   │   ├── models.py              # VerifiedValue, ModuleResult, Status, Confidence
│   │   ├── cross_validator.py     # Independent source cross-validation engine
│   │   ├── hal_interface.py       # HardwareReaderInterface
│   │   ├── platform_factory.py    # OS detection & HAL instantiation
│   │   └── windows/               # Windows implementation (WMI, Registry, SMART, NVML)
│   ├── infra/                     # Infrastructure services
│   │   ├── admin.py               # UAC elevation & token privilege checks
│   │   ├── logging.py             # Structured logging (Console + file)
│   │   ├── config.py              # Application settings & seller claims
│   │   └── errors.py              # Custom typed exception hierarchy
│   ├── tests_engine/              # Active verification & stress test engines
│   │   ├── orchestrator.py        # Scan lifecycle manager (Quick vs Full scan)
│   │   ├── benchmarks/            # Fake capacity tester & disk speed benchmarks
│   │   └── stress/                # CPU matrix stress, GPU shader stress, RAM pattern tests
│   ├── report/                    # Scoring & export engine
│   │   ├── scoring.py             # Weighted 0-100 scoring & red flag synthesizer
│   │   ├── claims_matcher.py      # Seller advertisement cross-matcher
│   │   ├── pdf_generator.py       # ReportLab certified PDF builder
│   │   └── json_exporter.py       # Machine-readable JSON export
│   └── ui/                        # PySide6 Qt6 modern UI
│       ├── theme.py               # Dark & Light theme stylesheets
│       ├── main_window.py         # Main application container & page navigation
│       ├── assets/                # Official Inspect Log logo & high-res icons (.ico, .png)
│       ├── pages/                 # Home, Scan Progress, and Results pages
│       ├── widgets/               # Module cards, claims dialog, consent modal
│       └── interactive/           # Keyboard, Mouse, Webcam, Mic, Tone, and Display test windows
├── tests/                         # Comprehensive pytest test suite (68 unit tests)
├── tools/
│   ├── smartmontools/             # Bundled smartctl.exe v7.5 drive diagnostic utility
│   └── build/                     # PyInstaller specification & Windows UAC manifest
├── pyproject.toml
└── README.md
```

---

## 💻 Developer Setup & Running from Source

### Requirements
- **Operating System**: Windows 10 (Build 1809+) or Windows 11 (64-bit)
- **Python**: 3.12 64-bit
- **Privileges**: Administrator privileges recommended

### 1. Clone & Set Up Environment
```powershell
git clone https://github.com/alonetiger/InspectLog.git
cd InspectLog

# Create and activate virtual environment
py -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

### 2. Run from Source
```powershell
# Launch GUI application
py -m hardwareverify
```

### 3. Run Automated Unit Tests
```powershell
py -m pytest -v
```

---

## 📦 Building Standalone Portable Executable

**Inspect Log** compiles into a single, self-contained, portable Windows executable (`InspectLog.exe`) requiring no Python installation on target machines. The build embeds the official UAC elevation manifest (`requireAdministrator`) to ensure SMART storage data and ACPI thermal sensors can be read.

### Build Command
```powershell
py -m PyInstaller tools/build/inspectlog.spec --clean --distpath dist --workpath build
```

Upon completion, the standalone executable will be located at:
```
dist/InspectLog.exe
```

---

## 🎨 Theme & Icons

Inspect Log uses the **Glass Transparent** theme: frosted translucent cards over an aurora gradient, in dark and light variants (toggle with the **Theme** button on the home screen).

Icons by [srip](https://www.flaticon.com/authors/srip) from [Flaticon](https://www.flaticon.com/), used under the Flaticon free license with attribution. See [`hardwareverify/ui/assets/icons/ATTRIBUTION.md`](hardwareverify/ui/assets/icons/ATTRIBUTION.md) for the full list.

---

## 🛡️ License & Disclaimers

Inspect Log is distributed under the MIT License.  
**Disclaimer**: Inspect Log provides diagnostic measurements and hardware telemetry based on operating system drivers and hardware-reported firmware. While it detects many common forms of component tampering and spoofing, hardware modifications involving low-level microcontroller spoofing may report simulated readings. Always exercise standard diligence when purchasing pre-owned electronics.
