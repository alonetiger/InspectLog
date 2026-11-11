"""Interactive dialog for entering seller advertised hardware specifications."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from hardwareverify.infra.config import SellerClaims
from hardwareverify.infra.logging import get_logger

logger = get_logger("claims_dialog")


class SellerClaimsDialog(QDialog):
    """Dialog allowing buyers to enter what the seller advertised before or after scanning."""

    def __init__(self, current_claims: SellerClaims, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("InspectLog — Enter Seller Advertised Claims")
        self.resize(540, 520)

        self.claims = current_claims
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Compare Against Seller's Advertisement")
        title.setObjectName("heroTitle")
        main_layout.addWidget(title)

        desc = QLabel(
            "Enter what the seller claimed in their listing or text message. "
            "InspectLog will highlight any shortfalls, fake specs, or downgraded components."
        )
        desc.setObjectName("textSecondary")
        desc.setWordWrap(True)
        main_layout.addWidget(desc)

        # Form container
        form_frame = QFrame()
        form_frame.setObjectName("cardFrame")
        form_layout = QFormLayout(form_frame)
        form_layout.setContentsMargins(20, 18, 20, 18)
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # CPU
        self.txt_cpu = QLineEdit()
        self.txt_cpu.setPlaceholderText("e.g. Intel Core i7-12700H or Ryzen 7 5800H")
        self.txt_cpu.setText(self.claims.cpu_model)
        form_layout.addRow("CPU Model:", self.txt_cpu)

        # RAM
        self.spn_ram = QSpinBox()
        self.spn_ram.setRange(0, 256)
        self.spn_ram.setSuffix(" GB")
        self.spn_ram.setValue(int(self.claims.ram_gb))
        form_layout.addRow("RAM Installed:", self.spn_ram)

        # Storage capacity
        self.spn_storage = QSpinBox()
        self.spn_storage.setRange(0, 8000)
        self.spn_storage.setSuffix(" GB")
        self.spn_storage.setSingleStep(128)
        self.spn_storage.setValue(int(self.claims.storage_gb))
        form_layout.addRow("Storage Size:", self.spn_storage)

        # Storage Type
        self.cmb_storage_type = QComboBox()
        self.cmb_storage_type.addItems(["Any / Unspecified", "SSD", "NVMe SSD", "HDD"])
        if self.claims.storage_type:
            idx = self.cmb_storage_type.findText(self.claims.storage_type)
            if idx >= 0:
                self.cmb_storage_type.setCurrentIndex(idx)
        form_layout.addRow("Storage Media:", self.cmb_storage_type)

        # GPU
        self.txt_gpu = QLineEdit()
        self.txt_gpu.setPlaceholderText("e.g. NVIDIA RTX 3060 or Integrated")
        self.txt_gpu.setText(self.claims.gpu_model)
        form_layout.addRow("GPU / Graphics:", self.txt_gpu)

        # Battery Health
        self.spn_battery = QSpinBox()
        self.spn_battery.setRange(0, 100)
        self.spn_battery.setSuffix("% Health (0 = Not claimed)")
        self.spn_battery.setValue(int(self.claims.battery_health_pct))
        form_layout.addRow("Claimed Battery:", self.spn_battery)

        # Display Resolution
        self.txt_res = QLineEdit()
        self.txt_res.setPlaceholderText("e.g. 1920x1080 or Full HD")
        self.txt_res.setText(self.claims.screen_resolution)
        form_layout.addRow("Screen Resolution:", self.txt_res)

        # Screen Size
        self.spn_size = QDoubleSpinBox()
        self.spn_size.setRange(0.0, 34.0)
        self.spn_size.setSingleStep(0.1)
        self.spn_size.setSuffix(' " Inches (0 = Unspecified)')
        self.spn_size.setValue(self.claims.screen_size_inches)
        form_layout.addRow("Screen Diagonal:", self.spn_size)

        main_layout.addWidget(form_frame)

        # Buttons
        btn_row = QHBoxLayout()
        btn_clear = QPushButton("Clear Claims")
        btn_clear.setObjectName("dangerButton")
        btn_clear.clicked.connect(self._clear_claims)
        btn_row.addWidget(btn_clear)

        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("secondaryButton")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton("Save & Compare")
        btn_save.clicked.connect(self._save_claims)
        btn_row.addWidget(btn_save)

        main_layout.addLayout(btn_row)

    def _clear_claims(self) -> None:
        self.txt_cpu.clear()
        self.spn_ram.setValue(0)
        self.spn_storage.setValue(0)
        self.cmb_storage_type.setCurrentIndex(0)
        self.txt_gpu.clear()
        self.spn_battery.setValue(0)
        self.txt_res.clear()
        self.spn_size.setValue(0.0)

    def _save_claims(self) -> None:
        st_type = self.cmb_storage_type.currentText()
        if st_type.startswith("Any"):
            st_type = ""

        self.claims.cpu_model = self.txt_cpu.text().strip()
        self.claims.ram_gb = float(self.spn_ram.value())
        self.claims.storage_gb = float(self.spn_storage.value())
        self.claims.storage_type = st_type
        self.claims.gpu_model = self.txt_gpu.text().strip()
        self.claims.battery_health_pct = float(self.spn_battery.value())
        self.claims.screen_resolution = self.txt_res.text().strip()
        self.claims.screen_size_inches = float(self.spn_size.value())

        logger.info("Saved seller claims: %s", self.claims)
        self.accept()
