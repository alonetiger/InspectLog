"""Application configuration manager."""

from dataclasses import dataclass, field


@dataclass
class ScanConfig:
    """Configuration for a scan run."""

    # Scan mode
    quick_scan: bool = True  # False = full test

    # CPU stress
    cpu_stress_duration_s: int = 30  # Quick: 30s, Full: 180s

    # Memory test
    memory_test_mb: int = 256  # Amount of RAM to test (MB)

    # Disk benchmark
    disk_benchmark_size_mb: int = 256  # Test file size

    # Battery
    discharge_sample_duration_s: int = 60  # Discharge rate sample time

    # Fake capacity test
    fake_capacity_test_external_only: bool = True  # Only test removable drives

    # Thermal safety
    thermal_emergency_stop_c: float = 95.0

    # Which modules to run (all by default)
    enabled_modules: list[str] = field(default_factory=lambda: [
        "system_identity",
        "battery",
        "storage",
        "ram",
        "cpu",
        "gpu",
        "display",
        "input_io",
        "thermals",
        "security",
    ])


@dataclass
class SellerClaims:
    """What the seller claims about the hardware."""

    cpu_model: str = ""
    ram_gb: float = 0.0
    storage_gb: float = 0.0
    storage_type: str = ""  # "SSD", "HDD", "NVMe"
    gpu_model: str = ""
    battery_health_pct: float = 0.0  # 0 means not claimed
    screen_resolution: str = ""
    screen_size_inches: float = 0.0

    @property
    def has_claims(self) -> bool:
        """Return True if any claims have been entered."""
        return any([
            self.cpu_model,
            self.ram_gb > 0,
            self.storage_gb > 0,
            self.storage_type,
            self.gpu_model,
            self.battery_health_pct > 0,
            self.screen_resolution,
            self.screen_size_inches > 0,
        ])


@dataclass
class AppConfig:
    """Top-level application config."""

    theme: str = "dark"  # "dark" or "light"
    scan: ScanConfig = field(default_factory=ScanConfig)
    seller_claims: SellerClaims = field(default_factory=SellerClaims)
