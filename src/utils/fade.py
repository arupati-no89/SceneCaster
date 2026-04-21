from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QObject
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget


def make_opacity_effect(widget: QWidget) -> QGraphicsOpacityEffect:
    """ウィジェットに QGraphicsOpacityEffect をセットして返す"""
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    return effect


def fade_animation(
    target: QObject,
    prop: bytes,
    start: float,
    end: float,
    duration_ms: int,
    easing: QEasingCurve.Type = QEasingCurve.Type.InOutCubic,
) -> QPropertyAnimation:
    """汎用フェードアニメーションを生成して返す（start 済み）"""
    anim = QPropertyAnimation(target, prop, target)
    anim.setDuration(max(duration_ms, 0))
    anim.setStartValue(float(start))
    anim.setEndValue(float(end))
    anim.setEasingCurve(easing)
    anim.start()
    return anim
