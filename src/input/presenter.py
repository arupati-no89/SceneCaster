from __future__ import annotations

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QKeyEvent


# コクヨ ELA-FP1 が送出するキーコード（実機確認前のデフォルト値）
# 実機テスト後にここを修正する。メモ帳等に入力して確認すること。
NEXT_KEYS: set[Qt.Key] = {
    Qt.Key.Key_PageDown,
    Qt.Key.Key_Right,
    Qt.Key.Key_Period,  # 一部モデルで . キーが「次」
}
PREV_KEYS: set[Qt.Key] = {
    Qt.Key.Key_PageUp,
    Qt.Key.Key_Left,
    Qt.Key.Key_Comma,   # 一部モデルで , キーが「前」
}
BLACKOUT_KEYS: set[Qt.Key] = {
    Qt.Key.Key_B,
    Qt.Key.Key_Period,  # ELA-FP1 の「黒画面」ボタン候補
}


class PresenterHandler(QObject):
    """HID キーボードとして認識されるプレゼンターの入力を処理する。

    MainWindow / ProjectionWindow の keyPressEvent からこのハンドラに
    イベントを転送することで、どちらにフォーカスがあっても動作する。
    """

    next_scene = Signal()
    prev_scene = Signal()
    blackout = Signal()

    def handle_key(self, event: QKeyEvent) -> bool:
        """キーイベントを処理し、消費した場合 True を返す"""
        key = Qt.Key(event.key())
        if key in NEXT_KEYS:
            self.next_scene.emit()
            return True
        if key in PREV_KEYS:
            self.prev_scene.emit()
            return True
        if key in BLACKOUT_KEYS:
            self.blackout.emit()
            return True
        return False
