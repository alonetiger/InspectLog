<div align="center">

# 🔍 Inspect Log

**Professional Hardware Genuineness, Component Health, & Anti-Fraud Verification Suite for Windows**

[![Platform: Windows 10 / 11](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D4?logo=windows)](https://microsoft.com/windows)
[![Python: 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://python.org)
[![GUI: PySide6 (Qt6)](https://img.shields.io/badge/GUI-PySide6%20%28Qt6%29-41CD52?logo=qt)](https://qt.io)
[![Test Suite: 67 Passing](https://img.shields.io/badge/Tests-67%20Passed-brightgreen?logo=pytest)](https://pytest.org)
[![Admin: Required](https://img.shields.io/badge/UAC-Administrator-critical)](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/user-account-control/)

</div>

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

### 4. 🧠 RAM Topography & Bit-Pattern Stress
- Enumerates total system memory, individual physical DIMM slots, capacity, form factor, memory type (DDR3/DDR4/DDR5), and manufacturer.
- Identifies **Dual-Channel vs. Single-Channel** memory channel topology.
- Flags underclocked memory running below rated XMP/JEDEC speeds.
- **Memory Pattern Test**: Executes a 4-pass bit-pattern stress test (Walking Ones `0x01`, Walking Zeros `0xFE`, Alternating `0xAA`/`0x55`, Random Noise) across free RAM buffers to detect bad cells or parity memory faults.

### 5. ⚡ CPU Genuineness & Thermal Throttling
- Reads CPU Model, Physical Cores, Logical Threads, Base/Boost Clocks, and L1/L2/L3 Cache architectures.
- **Anti-Spoofing Database**: Compares OS-reported CPU string against a verified reference database of Intel (Core i3/i5/i7/i9) and AMD (Ryzen 3/5/7/9) architectures. Detects hacked Windows registry strings where an old dual-core Celeron is masqueraded as a Core i9.
- **Multi-Core Stress Test**: Multi-threaded matrix stress workload with live clock speed and temperature monitoring.
- **Thermal Throttle Detection**: Analyzes CPU frequency curves under load; detects thermal drops $> 10\%$. Includes automated emergency cutoff at 95°C to protect test machines.

### 6. 🎮 GPU Verification & Stress
- Audits discrete and integrated GPUs, active driver versions, and verified Video RAM (VRAM) size (bypassing the legacy 32-bit 4 GB `AdapterRAM` WMI clamp via DirectX and Registry queries).
- Integrates `pynvml` (`nvidia-ml-py`) for real-time dedicated NVIDIA clock, fan, temperature, and power telemetry.
- GPU shader stress test with artifact detection and temperature logging.

### 7. 📺 Display Diagnostics & Fullscreen Pattern Generator
- Reads native panel resolution, refresh rate, and EDID physical diagonal screen dimensions ($\sqrt{w^2 + h^2} / 2.54$) via `WmiMonitorBasicDisplayParams`.
- Decodes 3-letter PNP manufacturer codes (Innolux, AU Optronics, LG Display, Samsung, BOE).
- **Fullscreen Diagnostic Suite**:
  - 7 test patterns: Pure Red, Green, Blue, Black (backlight bleed), White, 50% Grey (uniformity), and 256-level RGB Gradient (banding).
  - Floating HUD with keyboard hotkeys (`Space`, `P`, `F`, `Esc`).

### 8. ⌨️ Input, Audio, Camera & I/O Diagnostics
- **Interactive Keyboard Map**: Visual ANSI keyboard layout where every key lights up green upon physical actuation with press counters and verified key percentage.
- **Mouse & Touchpad Tester**: Visual mouse canvas validating Left, Right, Middle click, Double-click, Scroll Wheel delta, and cursor tracking trajectory.
- **Audio Channel Separation**: Synthesizes genuine 16-bit 44.1 kHz stereo audio waveforms with 100% channel isolation (Left channel 440 Hz / Right silent, then Right channel / Left silent).
- **Microphone Level Meter**: Real-time RMS decibel volume bar and voice activity detection via `QAudioSource`.
- **Webcam Optical Preview**: Live camera feed powered by `QMediaCaptureSession` and `QVideoWidget`.
- **Real-Time USB Port Detector**: Live event monitor tracking insertion/removal of flash drives, dongles, and peripherals across all USB ports.
- **Wireless Diagnostics**: Scans Wi-Fi interfaces, active SSID, BSSID, Signal Quality, 802.11 physical standards, and Bluetooth controller status.

### 9. 🌡️ Thermals & Security Audit
- Live thermal zones via ACPI `MSAcpi_ThermalZoneTemperature` and discrete GPU sensors.
- Hardware security verification: Secure Boot state, TPM (Trusted Platform Module) version, and Enterprise MDM enrollment check (Activation Lock / Intune / corporate fleet management flags).

### 10. 📊 Health Scoring, Claims Matcher & Certified PDF Report
- **Weighted 0–100 Health Score**: Component weights calibrated by failure impact (Storage 20%, Battery 15%, CPU 15%, RAM 10%, GPU 10%, Display 10%, etc.).
- **Plain-Language Red Flags & Buyer Advice**: Generates actionable price negotiation advice (e.g., *"Battery has lost 37% of design capacity. Negotiate price down or budget for replacement."*).
- **Seller-Claims Matcher**: Compare the seller's advertisement (CPU, RAM, Storage, GPU, Battery) against actual test results with token-aware matching and tolerance bounds.
- **Certified PDF & JSON Export**: Generates professional multi-page reports featuring the official Inspect Log header, system serial number, QR/timestamp metadata, color-coded status badges, and complete data provenance.

---

## 🏗️ Architecture & Project Structure

```
HardwareVerify/
├── hardwareverify/
│   ├── constants.py               # Global settings, paths, thresholds, PyInstaller bundle resolver
│   ├── app.py                     # Qt application bootstrap & lifecycle
│   ├── __main__.py                # CLI entry point (py -m hardwareverify)
│   ├── core/                      # Hardware abstraction layer (HAL)
│   │   ├── models.py              # Strongly-typed data models (VerifiedValue, ModuleResult, Status)
│   │   ├── hal_interface.py       # Base reader interfaces
│   │   ├── cross_validator.py     # Multi-source confidence engine
│   │   ├── platform_factory.py    # OS platform dispatch (Windows / Linux / macOS)
│   │   └── windows/               # Windows low-level readers (WMI, SMART, EDID, Registry, netsh)
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
├── tests/                         # Comprehensive pytest test suite (67 unit tests)
├── tools/
│   ├── smartmontools/             # Bundled smartctl.exe v7.5 drive diagnostic utility
│   └── build/                     # PyInstaller specification & Windows UAC manifest
├── pyproject.toml
└── README.md
```

---

## 💻 Prerequisites & Installation

### Requirements
- **Operating System**: Windows 10 (Build 1809+) or Windows 11 (64-bit)
- **Python**: 3.12 64-bit
- **Privileges**: Administrator privileges recommended (required for drive SMART NVMe/ATA pass-through and ACPI thermal queries)

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
# Build single-file executable using the included spec
py -m PyInstaller tools/build/inspectlog.spec --clean --distpath dist --workpath build
```

Upon completion, the standalone executable will be located at:
```
dist/InspectLog.exe
```

---

## 🛡️ License & Disclaimers

Inspect Log is distributed under the MIT License.
**Disclaimer**: Inspect Log provides diagnostic measurements and hardware telemetry based on operating system drivers and hardware-reported firmware. While it detects many common forms of component tampering and spoofing, hardware modifications involving low-level microcontroller spoofing may report simulated readings. Always exercise standard diligence when purchasing pre-owned electronics.
