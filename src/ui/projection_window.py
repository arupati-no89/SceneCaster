from __future__ import annotations

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QColor, QPainter, QScreen
from PySide6.QtWidgets import QWidget, QLabel, QStackedLayout, QApplication


class _ImageLayer(QLabel):
    """単一画像を表示する透過可能レイヤー"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background: black;")
        self._pixmap: QPixmap | None = None

    def set_image(self, path: str | None) -> None:
        if path is None:
            self._pixmap = None
            self.setPixmap(QPixmap())
        else:
            self._pixmap = QPixmap(path)
            self._scale_to_fit()

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._scale_to_fit()

    def _scale_to_fit(self) -> None:
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            super().setPixmap(scaled)


class ProjectionWindow(QWidget):
    """プロジェクター／外部ディスプレイへの投影ウィンドウ"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SceneCaster — Projection")
        self.setStyleSheet("background: black;")
        self.setMinimumSize(800, 450)

        self._is_fullscreen = False
        self._blackout = False

        # 2枚のレイヤーをクロスフェードに使う
        self._layer_a = _ImageLayer(self)
        self._layer_b = _ImageLayer(self)
        self._layer_b.setWindowOpacity(0.0)

        # どちらが前面か
        self._front: _ImageLayer = self._layer_a
        self._back: _ImageLayer = self._layer_b

        # ブラックアウト用オーバーレイ
        self._blackout_overlay = QWidget(self)
        self._blackout_overlay.setStyleSheet("background: black;")
        self._blackout_overlay.hide()

        # フェードアニメーション
        self._anim: QPropertyAnimation | None = None

        self._resize_layers()

    # ------------------------------------------------------------------
    # 公開 API
    # ------------------------------------------------------------------

    def set_screen(self, screen: QScreen) -> None:
        """投影先の物理ディスプレイを指定する"""
        self.setGeometry(screen.geometry())

    def show_fullscreen_on(self, screen: QScreen) -> None:
        self.set_screen(screen)
        self.showFullScreen()
        self._is_fullscreen = True

    def toggle_fullscreen(self) -> None:
        if self._is_fullscreen:
            self.showNormal()
            self._is_fullscreen = False
        else:
            self.showFullScreen()
            self._is_fullscreen = True

    def set_blackout(self, enabled: bool) -> None:
        self._blackout = enabled
        if enabled:
            self._blackout_overlay.setGeometry(self.rect())
            self._blackout_overlay.raise_()
            self._blackout_overlay.show()
        else:
            self._blackout_overlay.hide()

    def toggle_blackout(self) -> None:
        self.set_blackout(not self._blackout)

    @property
    def is_blackout(self) -> bool:
        return self._blackout

    def transition_to(self, image_path: str | None, fade_ms: int = 1500) -> None:
        """画像をクロスフェードで切り替える"""
        # 停止中のアニメーションがあれば終了
        if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()

        # back レイヤーに新画像をセット（現時点では透明）
        self._back.set_image(image_path)
        self._back.setWindowOpacity(0.0)
        self._back.raise_()

        if fade_ms <= 0:
            self._back.setWindowOpacity(1.0)
            self._front.setWindowOpacity(0.0)
            self._swap_layers()
            return

        self._anim = QPropertyAnimation(self._back, b"windowOpacity")
        self._anim.setDuration(fade_ms)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim.finished.connect(self._on_fade_done)
        self._anim.start()

    # ------------------------------------------------------------------
    # 内部処理
    # ------------------------------------------------------------------

    def _on_fade_done(self) -> None:
        self._front.setWindowOpacity(0.0)
        self._swap_layers()

    def _swap_layers(self) -> None:
        self._front, self._back = self._back, self._front

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._resize_layers()
        if self._blackout:
            self._blackout_overlay.setGeometry(self.rect())

    def _resize_layers(self) -> None:
        for layer in (self._layer_a, self._layer_b):
            layer.setGeometry(self.rect())
