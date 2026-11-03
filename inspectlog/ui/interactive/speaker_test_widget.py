"""Interactive Speaker and Stereo Separation diagnostic widget."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from inspectlog.infra.logging import get_logger
from inspectlog.ui.interactive.audio_tone_generator import play_channel_tone

logger = get_logger("speaker_test_widget")


class SpeakerTestWidget(QWidget):
    """Audio output and stereo channel separation verification tab."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.left_verified = False
        self.right_verified = False

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        header_row = QHBoxLayout()
        lbl_title = QLabel("Speaker & Stereo Channel Verification")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #E2E8F0;")
        header_row.addWidget(lbl_title)
        header_row.addStretch()
        layout.addLayout(header_row)

        desc = QLabel(
            "Verify that your laptop speakers or connected headphones produce sound in the correct channel "
            "without distortion, crackling, or channel crosstalk. Click each button below to play a 440 Hz test tone."
        )
        desc.setStyleSheet("color: #94A3B8; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 2 Channel Cards (Left and Right)
        cards_row = QHBoxLayout()
        cards_row.setSpacing(20)

        # --- Left Channel Card ---
        left_card = QFrame()
        left_card.setStyleSheet("""
            QFrame {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        left_layout = QVBoxLayout(left_card)
        left_layout.setSpacing(12)

        lbl_l_icon = QLabel("🔊 Left Channel")
        lbl_l_icon.setStyleSheet("font-size: 15px; font-weight: 700; color: #38BDF8;")
        left_layout.addWidget(lbl_l_icon)

        lbl_l_desc = QLabel("Should play exclusively from the left speaker or left headphone earcup.")
        lbl_l_desc.setStyleSheet("color: #94A3B8; font-size: 12px;")
        lbl_l_desc.setWordWrap(True)
        left_layout.addWidget(lbl_l_desc)

        self.btn_play_left = QPushButton("▶ Play Left Tone (440 Hz)")
        self.btn_play_left.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: white;
                font-weight: 600;
                padding: 10px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #0369A1; }
        """)
        self.btn_play_left.clicked.connect(self._play_left)
        left_layout.addWidget(self.btn_play_left)

        l_verdict_row = QHBoxLayout()
        self.btn_l_pass = QPushButton("✓ Heard Clearly")
        self.btn_l_pass.setStyleSheet("""
            QPushButton {
                background-color: #064E3B;
                color: #34D399;
                font-weight: 600;
                padding: 6px 12px;
                border-radius: 6px;
                border: 1px solid #059669;
            }
            QPushButton:hover { background-color: #059669; color: white; }
        """)
        self.btn_l_pass.clicked.connect(self._mark_left_pass)
        l_verdict_row.addWidget(self.btn_l_pass)

        self.btn_l_fail = QPushButton("✕ Silent / Broken")
        self.btn_l_fail.setStyleSheet("""
            QPushButton {
                background-color: #450A0A;
                color: #F87171;
                font-weight: 600;
                padding: 6px 12px;
                border-radius: 6px;
                border: 1px solid #991B1B;
            }
            QPushButton:hover { background-color: #991B1B; color: white; }
        """)
        self.btn_l_fail.clicked.connect(self._mark_left_fail)
        l_verdict_row.addWidget(self.btn_l_fail)
        left_layout.addLayout(l_verdict_row)

        self.lbl_l_status = QLabel("Status: Not Tested")
        self.lbl_l_status.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600;")
        left_layout.addWidget(self.lbl_l_status)

        cards_row.addWidget(left_card)

        # --- Right Channel Card ---
        right_card = QFrame()
        right_card.setStyleSheet("""
            QFrame {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        right_layout = QVBoxLayout(right_card)
        right_layout.setSpacing(12)

        lbl_r_icon = QLabel("🔊 Right Channel")
        lbl_r_icon.setStyleSheet("font-size: 15px; font-weight: 700; color: #38BDF8;")
        right_layout.addWidget(lbl_r_icon)

        lbl_r_desc = QLabel("Should play exclusively from the right speaker or right headphone earcup.")
        lbl_r_desc.setStyleSheet("color: #94A3B8; font-size: 12px;")
        lbl_r_desc.setWordWrap(True)
        right_layout.addWidget(lbl_r_desc)

        self.btn_play_right = QPushButton("▶ Play Right Tone (440 Hz)")
        self.btn_play_right.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: white;
                font-weight: 600;
                padding: 10px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #0369A1; }
        """)
        self.btn_play_right.clicked.connect(self._play_right)
        right_layout.addWidget(self.btn_play_right)

        r_verdict_row = QHBoxLayout()
        self.btn_r_pass = QPushButton("✓ Heard Clearly")
        self.btn_r_pass.setStyleSheet("""
            QPushButton {
                background-color: #064E3B;
                color: #34D399;
                font-weight: 600;
                padding: 6px 12px;
                border-radius: 6px;
                border: 1px solid #059669;
            }
            QPushButton:hover { background-color: #059669; color: white; }
        """)
        self.btn_r_pass.clicked.connect(self._mark_right_pass)
        r_verdict_row.addWidget(self.btn_r_pass)

        self.btn_r_fail = QPushButton("✕ Silent / Broken")
        self.btn_r_fail.setStyleSheet("""
            QPushButton {
                background-color: #450A0A;
                color: #F87171;
                font-weight: 600;
                padding: 6px 12px;
                border-radius: 6px;
                border: 1px solid #991B1B;
            }
            QPushButton:hover { background-color: #991B1B; color: white; }
        """)
        self.btn_r_fail.clicked.connect(self._mark_right_fail)
        r_verdict_row.addWidget(self.btn_r_fail)
        right_layout.addLayout(r_verdict_row)

        self.lbl_r_status = QLabel("Status: Not Tested")
        self.lbl_r_status.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600;")
        right_layout.addWidget(self.lbl_r_status)

        cards_row.addWidget(right_card)
        layout.addLayout(cards_row)

        # Both channels button
        both_row = QHBoxLayout()
        self.btn_play_both = QPushButton("▶ Test Stereo Full Center (Both Channels)")
        self.btn_play_both.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #E2E8F0;
                font-weight: 600;
                padding: 8px 18px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        self.btn_play_both.clicked.connect(self._play_both)
        both_row.addWidget(self.btn_play_both)
        both_row.addStretch()

        self.lbl_overall = QLabel("Overall: Pending channel tests")
        self.lbl_overall.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: 600;")
        both_row.addWidget(self.lbl_overall)
        layout.addLayout(both_row)

    def _play_left(self) -> None:
        self.lbl_l_status.setText("Status: Playing Left channel...")
        self.lbl_l_status.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 600;")
        play_channel_tone(left=True, right=False)

    def _play_right(self) -> None:
        self.lbl_r_status.setText("Status: Playing Right channel...")
        self.lbl_r_status.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 600;")
        play_channel_tone(left=False, right=True)

    def _play_both(self) -> None:
        play_channel_tone(left=True, right=True)

    def _mark_left_pass(self) -> None:
        self.left_verified = True
        self.lbl_l_status.setText("Status: ✓ Left Channel Verified")
        self.lbl_l_status.setStyleSheet("color: #10B981; font-size: 12px; font-weight: 600;")
        self._update_overall()

    def _mark_left_fail(self) -> None:
        self.left_verified = False
        self.lbl_l_status.setText("Status: ✕ Left Channel Failed")
        self.lbl_l_status.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: 600;")
        self._update_overall()

    def _mark_right_pass(self) -> None:
        self.right_verified = True
        self.lbl_r_status.setText("Status: ✓ Right Channel Verified")
        self.lbl_r_status.setStyleSheet("color: #10B981; font-size: 12px; font-weight: 600;")
        self._update_overall()

    def _mark_right_fail(self) -> None:
        self.right_verified = False
        self.lbl_r_status.setText("Status: ✕ Right Channel Failed")
        self.lbl_r_status.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: 600;")
        self._update_overall()

    def _update_overall(self) -> None:
        if self.left_verified and self.right_verified:
            self.lbl_overall.setText("Overall: ✓ Stereo Separation Verified")
            self.lbl_overall.setStyleSheet("color: #10B981; font-size: 13px; font-weight: 700;")
        elif self.left_verified or self.right_verified:
            self.lbl_overall.setText("Overall: ⚠ Partial Verification")
            self.lbl_overall.setStyleSheet("color: #F59E0B; font-size: 13px; font-weight: 600;")

    def get_test_summary(self) -> dict[str, Any]:
        """Return verification outcome for report generation."""
        return {
            "left_channel": self.left_verified,
            "right_channel": self.right_verified,
            "passed": self.left_verified and self.right_verified,
        }
