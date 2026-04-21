from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QGroupBox, QGridLayout, QLabel, QSlider, QSpinBox,
)


class _EqRow:
    """ラベル + スライダー（-12〜+12 dB）+ 数値表示 の1行"""

    def __init__(self, label: str, layout: QGridLayout, row: int) -> None:
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(-12, 12)
        self.slider.setValue(0)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.setTickInterval(6)

        self.spinbox = QSpinBox()
        self.spinbox.setRange(-12, 12)
        self.spinbox.setValue(0)
        self.spinbox.setSuffix("dB")
        self.spinbox.setFixedWidth(64)

        layout.addWidget(QLabel(label), row, 0)
        layout.addWidget(self.slider, row, 1)
        layout.addWidget(self.spinbox, row, 2)

        self.slider.valueChanged.connect(self.spinbox.setValue)
        self.spinbox.valueChanged.connect(self.slider.setValue)

    def connect(self, callback) -> None:
        self.slider.valueChanged.connect(callback)

    @property
    def value(self) -> float:
        return float(self.slider.value())


class EqPanelWidget(QGroupBox):
    """Bass / Mid / Treble の3バンドイコライザー"""

    bass_changed   = Signal(float)
    mid_changed    = Signal(float)
    treble_changed = Signal(float)

    def __init__(self, parent=None) -> None:
        super().__init__("イコライザー", parent)
        layout = QGridLayout(self)
        layout.setColumnStretch(1, 1)

        self._bass   = _EqRow("Bass (100Hz)",  layout, 0)
        self._mid    = _EqRow("Mid  (1kHz)",   layout, 1)
        self._treble = _EqRow("Treble (8kHz)", layout, 2)

        self._bass.connect(lambda v: self.bass_changed.emit(float(v)))
        self._mid.connect(lambda v: self.mid_changed.emit(float(v)))
        self._treble.connect(lambda v: self.treble_changed.emit(float(v)))
