"""Interactive Webcam preview and image sensor diagnostic widget."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtMultimedia import (
    QCamera,
    QCameraDevice,
    QImageCapture,
    QMediaCaptureSession,
    QMediaDevices,
)
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from hardwareverify.infra.logging import get_logger

logger = get_logger("webcam_test_widget")


class WebcamTestWidget(QWidget):
    """Webcam video feed and sensor verification tab."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._camera: QCamera | None = None
        self._capture_session: QMediaCaptureSession | None = None
        self._image_capture: QImageCapture | None = None
        self._verified = False
        self._devices: list[QCameraDevice] = []

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)

        header_row = QHBoxLayout()
        lbl_title = QLabel("Webcam & Video Sensor Diagnostic")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #E2E8F0;")
        header_row.addWidget(lbl_title)
        header_row.addStretch()
        layout.addLayout(header_row)

        desc = QLabel(
            "Select your camera device below and click 'Start Camera' to verify optical focus, "
            "color reproduction, and driver video capture pipeline."
        )
        desc.setStyleSheet("color: #94A3B8; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Device selector row
        dev_row = QHBoxLayout()
        lbl_dev = QLabel("Camera Device:")
        lbl_dev.setStyleSheet("color: #CBD5E1; font-weight: 600; font-size: 13px;")
        dev_row.addWidget(lbl_dev)

        self.cmb_cameras = QComboBox()
        self.cmb_cameras.setStyleSheet("""
            QComboBox {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
                min-width: 280px;
            }
        """)
        self._populate_cameras()
        dev_row.addWidget(self.cmb_cameras, 1)

        self.btn_toggle = QPushButton("Start Camera")
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: white;
                font-weight: 600;
                padding: 6px 16px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #0369A1; }
        """)
        self.btn_toggle.clicked.connect(self._toggle_camera)
        dev_row.addWidget(self.btn_toggle)

        layout.addLayout(dev_row)

        # Video Viewport Container
        self.viewport_frame = QFrame()
        self.viewport_frame.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 10px;
            }
        """)
        viewport_layout = QVBoxLayout(self.viewport_frame)
        viewport_layout.setContentsMargins(6, 6, 6, 6)

        self.video_widget = QVideoWidget(self.viewport_frame)
        self.video_widget.setMinimumSize(480, 270)
        viewport_layout.addWidget(self.video_widget)

        layout.addWidget(self.viewport_frame, 1)

        # Action and verdict row
        act_row = QHBoxLayout()
        self.btn_pass = QPushButton("✓ Camera Verified (Video OK)")
        self.btn_pass.setStyleSheet("""
            QPushButton {
                background-color: #064E3B;
                color: #34D399;
                font-weight: 600;
                padding: 8px 18px;
                border-radius: 6px;
                border: 1px solid #059669;
            }
            QPushButton:hover { background-color: #059669; color: white; }
        """)
        self.btn_pass.clicked.connect(self._mark_verified)
        act_row.addWidget(self.btn_pass)

        self.btn_fail = QPushButton("✕ Camera Defect / Blank Feed")
        self.btn_fail.setStyleSheet("""
            QPushButton {
                background-color: #450A0A;
                color: #F87171;
                font-weight: 600;
                padding: 8px 18px;
                border-radius: 6px;
                border: 1px solid #991B1B;
            }
            QPushButton:hover { background-color: #991B1B; color: white; }
        """)
        self.btn_fail.clicked.connect(self._mark_failed)
        act_row.addWidget(self.btn_fail)

        act_row.addStretch()

        self.lbl_verdict = QLabel("Verdict: Pending Test")
        self.lbl_verdict.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: 600;")
        act_row.addWidget(self.lbl_verdict)

        layout.addLayout(act_row)

    def _populate_cameras(self) -> None:
        try:
            self._devices = QMediaDevices.videoInputs()
            self.cmb_cameras.clear()
            for dev in self._devices:
                self.cmb_cameras.addItem(dev.description(), dev)
            if not self._devices:
                self.cmb_cameras.addItem("No video input devices detected", None)
                self.btn_toggle.setEnabled(False)
        except Exception as e:
            logger.warning("Failed to list video inputs: %s", e)

    def _toggle_camera(self) -> None:
        if self._camera and self._camera.isActive():
            self._stop_camera()
        else:
            self._start_camera()

    def _start_camera(self) -> None:
        idx = self.cmb_cameras.currentIndex()
        if idx < 0 or not self._devices:
            return

        device: QCameraDevice = self._devices[idx]
        try:
            self._camera = QCamera(device, self)
            self._capture_session = QMediaCaptureSession(self)
            self._capture_session.setCamera(self._camera)
            self._capture_session.setVideoOutput(self.video_widget)

            self._camera.start()

            self.btn_toggle.setText("Stop Camera")
            self.btn_toggle.setStyleSheet("""
                QPushButton {
                    background-color: #DC2626;
                    color: white;
                    font-weight: 600;
                    padding: 6px 16px;
                    border-radius: 6px;
                    border: none;
                }
                QPushButton:hover { background-color: #EF4444; }
            """)
        except Exception as e:
            logger.error("Failed to start camera: %s", e)
            self.lbl_verdict.setText(f"Error: {e}")

    def _stop_camera(self) -> None:
        if self._camera:
            try:
                self._camera.stop()
            except Exception:
                pass
            self._camera = None
            self._capture_session = None

        self.btn_toggle.setText("Start Camera")
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: white;
                font-weight: 600;
                padding: 6px 16px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #0369A1; }
        """)

    def _mark_verified(self) -> None:
        self._verified = True
        self.lbl_verdict.setText("Verdict: ✓ Camera Verified Working")
        self.lbl_verdict.setStyleSheet("color: #10B981; font-size: 13px; font-weight: 700;")

    def _mark_failed(self) -> None:
        self._verified = False
        self.lbl_verdict.setText("Verdict: ✕ Camera Defect Reported")
        self.lbl_verdict.setStyleSheet("color: #EF4444; font-size: 13px; font-weight: 700;")

    def closeEvent(self, event) -> None:
        self._stop_camera()
        super().closeEvent(event)

    def get_test_summary(self) -> dict[str, Any]:
        """Return verification outcome for report generation."""
        return {
            "camera_count": len(self._devices),
            "camera_name": self.cmb_cameras.currentText(),
            "passed": self._verified,
        }
