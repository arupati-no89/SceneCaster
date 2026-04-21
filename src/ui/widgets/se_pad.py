from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox, QGridLayout, QPushButton, QScrollArea, QWidget, QVBoxLayout,
)

from src.models.scenario import SeButton

_COLS = 3   # グリッドの列数


class SePadWidget(QGroupBox):
    """SE ワンショットボタンパッド"""

    se_triggered = Signal(str, float)   # (file, volume)

    def __init__(self, parent=None) -> None:
        super().__init__("SE", parent)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._inner = QWidget()
        self._grid = QGridLayout(self._inner)
        self._grid.setSpacing(4)
        scroll.setWidget(self._inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.addWidget(scroll)

        self._buttons: list[QPushButton] = []

    def load_buttons(self, shared: list[SeButton], scene_specific: list[SeButton]) -> None:
        self._clear()
        all_se = list(shared) + list(scene_specific)
        for i, se in enumerate(all_se):
            btn = QPushButton(se.label)
            btn.setToolTip(se.file)
            btn.setFixedHeight(40)
            # シーン固有SEはボタン色を変えて区別
            if i >= len(shared):
                btn.setStyleSheet("QPushButton { background: #2a4a2a; }")
            file, volume = se.file, se.volume
            btn.clicked.connect(lambda _=False, f=file, v=volume: self.se_triggered.emit(f, v))
            self._grid.addWidget(btn, i // _COLS, i % _COLS)
            self._buttons.append(btn)

    def _clear(self) -> None:
        for btn in self._buttons:
            btn.deleteLater()
        self._buttons.clear()
