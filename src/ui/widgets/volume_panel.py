from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QGroupBox, QGridLayout, QLabel, QSlider, QSpinBox,
)


class _VolumeRow:
    """ラベル + スライダー + 数値表示 の1行"""

    def __init__(self, label: str, layout: QGridLayout, row: int) -> None:
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(100)

        self.spinbox = QSpinBox()
        self.spinbox.setRange(0, 100)
        self.spinbox.setValue(100)
        self.spinbox.setSuffix("%")
        self.spinbox.setFixedWidth(64)

        layout.addWidget(QLabel(label), row, 0)
        layout.addWidget(self.slider, row, 1)
        layout.addWidget(self.spinbox, row, 2)

        # 双方向同期
        self.slider.valueChanged.connect(self.spinbox.setValue)
        self.spinbox.valueChanged.connect(self.slider.setValue)

    def connect(self, callback) -> None:
        self.slider.valueChanged.connect(callback)

    @property
    def value(self) -> float:
        return self.slider.value() / 100.0


class VolumePanelWidget(QGroupBox):
    """マスター / BGM / 環境音 / SE の音量スライダー群"""

    master_changed = Signal(float)
    bgm_changed = Signal(float)
    ambient_changed = Signal(float)
    se_changed = Signal(float)

    def __init__(self, parent=None) -> None:
        super().__init__("音量", parent)
        layout = QGridLayout(self)
        layout.setColumnStretch(1, 1)

        self._master = _VolumeRow("マスター", layout, 0)
        self._bgm = _VolumeRow("BGM", layout, 1)
        self._ambient = _VolumeRow("環境音", layout, 2)
        self._se = _VolumeRow("SE", layout, 3)

        self._master.connect(lambda v: self.master_changed.emit(v / 100.0))
        self._bgm.connect(lambda v: self.bgm_changed.emit(v / 100.0))
        self._ambient.connect(lambda v: self.ambient_changed.emit(v / 100.0))
        self._se.connect(lambda v: self.se_changed.emit(v / 100.0))
