from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem

from src.models.scenario import Scene


class SceneListWidget(QListWidget):
    """シーン一覧を表示し、選択シーンを通知するウィジェット"""

    scene_selected = Signal(int)  # 選択されたシーンのインデックス

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(200)
        self.currentRowChanged.connect(self.scene_selected)

    def load_scenes(self, scenes: list[Scene]) -> None:
        self.blockSignals(True)
        self.clear()
        for i, scene in enumerate(scenes):
            item = QListWidgetItem(f"{i + 1:02d}. {scene.title}")
            item.setToolTip(scene.scene_id)
            self.addItem(item)
        self.blockSignals(False)
        if self.count() > 0:
            self.setCurrentRow(0)

    def select_scene(self, index: int) -> None:
        if 0 <= index < self.count():
            self.blockSignals(True)
            self.setCurrentRow(index)
            self.blockSignals(False)
