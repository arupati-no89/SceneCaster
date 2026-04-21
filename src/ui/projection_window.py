from __future__ import annotations

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Signal
from PySide6.QtGui import QPixmap, QScreen, QKeyEvent
from PySide6.QtWidgets import QWidget, QLabel, QGraphicsOpacityEffect

from src.utils.fade import make_opacity_effect, fade_animation

_BLACKOUT_FADE_MS = 300


class _ImageLayer(QLabel):
    """画像を1枚表示する透過可能レイヤー"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background: black;")
        self._pixmap_src: QPixmap | None = None
        self._effect = make_opacity_effect(self)

    # ------------------------------------------------------------------
    # 不透明度プロパティ（QPropertyAnimation のターゲットは effect）
    # ------------------------------------------------------------------

    def set_opacity(self, value: float) -> None:
        self._effect.setOpacity(value)

    def get_opacity(self) -> float:
        return self._effect.opacity()

    # ------------------------------------------------------------------

    def set_image(self, path: str | None) -> None:
        if path is None:
            self._pixmap_src = None
            super().setPixmap(QPixmap())
        else:
            px = QPixmap(path)
            self._pixmap_src = px if not px.isNull() else None
            self._render()

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._render()

    def _render(self) -> None:
        if self._pixmap_src and not self._pixmap_src.isNull():
            scaled = self._pixmap_src.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            super().setPixmap(scaled)
        else:
            super().setPixmap(QPixmap())


class ProjectionWindow(QWidget):
    """プロジェクター／外部ディスプレイへの投影ウィンドウ"""

    key_pressed = Signal(QKeyEvent)   # GM操作ウィンドウへ転送するためのシグナル

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SceneCaster — Projection")
        self.setStyleSheet("background: black;")
        self.setMinimumSize(800, 450)

        self._is_fullscreen = False
        self._blackout = False

        # 2枚のレイヤーでクロスフェード
        self._layer_a = _ImageLayer(self)
        self._layer_b = _ImageLayer(self)
        self._layer_a.set_opacity(1.0)
        self._layer_b.set_opacity(0.0)
        self._front: _ImageLayer = self._layer_a   # 現在表示中
        self._back: _ImageLayer = self._layer_b    # 次の画像を準備

        # ブラックアウト用オーバーレイ
        self._blackout_overlay = QWidget(self)
        self._blackout_overlay.setStyleSheet("background: black;")
        self._bo_effect = make_opacity_effect(self._blackout_overlay)
        self._bo_effect.setOpacity(0.0)
        self._blackout_overlay.hide()

        # アニメーション参照（GC防止）
        self._cross_anim_in: QPropertyAnimation | None = None
        self._cross_anim_out: QPropertyAnimation | None = None
        self._bo_anim: QPropertyAnimation | None = None

        self._resize_layers()

    # ------------------------------------------------------------------
    # 公開 API
    # ------------------------------------------------------------------

    def set_screen(self, screen: QScreen) -> None:
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
        if self._bo_anim:
            self._bo_anim.stop()

        if enabled:
            self._blackout_overlay.setGeometry(self.rect())
            self._blackout_overlay.raise_()
            self._blackout_overlay.show()
            self._bo_anim = fade_animation(
                self._bo_effect, b"opacity",
                self._bo_effect.opacity(), 1.0, _BLACKOUT_FADE_MS,
            )
        else:
            self._bo_anim = fade_animation(
                self._bo_effect, b"opacity",
                self._bo_effect.opacity(), 0.0, _BLACKOUT_FADE_MS,
            )
            self._bo_anim.finished.connect(self._blackout_overlay.hide)

    def toggle_blackout(self) -> None:
        self.set_blackout(not self._blackout)

    @property
    def is_blackout(self) -> bool:
        return self._blackout

    def transition_to(self, image_path: str | None, fade_ms: int = 1500) -> None:
        """クロスフェードで画像を切り替える"""
        # 進行中のクロスフェードを即完了させる
        if self._cross_anim_in and self._cross_anim_in.state() == QPropertyAnimation.State.Running:
            self._cross_anim_in.stop()
            self._cross_anim_out.stop()
            self._front.set_opacity(0.0)
            self._back.set_opacity(1.0)
            self._swap_layers()

        # back に新画像を配置（透明）
        self._back.set_image(image_path)
        self._back.set_opacity(0.0)
        self._back.raise_()

        if fade_ms <= 0:
            self._back.set_opacity(1.0)
            self._front.set_opacity(0.0)
            self._swap_layers()
            return

        # back をフェードイン、front をフェードアウト（同時進行）
        self._cross_anim_in = fade_animation(
            self._back._effect, b"opacity", 0.0, 1.0, fade_ms,
        )
        self._cross_anim_out = fade_animation(
            self._front._effect, b"opacity", 1.0, 0.0, fade_ms,
        )
        self._cross_anim_in.finished.connect(self._on_crossfade_done)

    # ------------------------------------------------------------------
    # 内部処理
    # ------------------------------------------------------------------

    def _on_crossfade_done(self) -> None:
        self._swap_layers()

    def _swap_layers(self) -> None:
        self._front, self._back = self._back, self._front

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._resize_layers()
        if self._blackout:
            self._blackout_overlay.setGeometry(self.rect())

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        self.key_pressed.emit(event)

    def _resize_layers(self) -> None:
        for layer in (self._layer_a, self._layer_b):
            layer.setGeometry(self.rect())
