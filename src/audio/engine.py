from __future__ import annotations

import threading
from dataclasses import dataclass, field

import pygame

from src.models.scenario import Scene, DuckSettings

_BGM_CHANNEL_FADE_MS = 50   # pygame.mixer.music のフェード精度限界への対策
_AMBIENT_CHANNEL = 0
_SE_CHANNEL_START = 1
_SE_CHANNEL_END = 15        # 1〜15 の 15ch を SE 用に確保


@dataclass
class _VolumeState:
    master: float = 1.0
    bgm: float = 1.0
    ambient: float = 1.0
    se: float = 1.0

    def effective_bgm(self) -> float:
        return self.master * self.bgm

    def effective_ambient(self) -> float:
        return self.master * self.ambient

    def effective_se(self) -> float:
        return self.master * self.se


class AudioEngine:
    """pygame.mixer ラッパー。BGM / 環境音 / SE の3レーンを管理する。"""

    def __init__(self) -> None:
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(16)

        self._vol = _VolumeState()
        self._bgm_base_vol: float = 1.0   # ダッキング前のBGM音量
        self._duck_count: int = 0          # 現在再生中SEの数（ダッキング管理）
        self._duck_settings: DuckSettings = DuckSettings()
        self._lock = threading.Lock()

        self._ambient_channel = pygame.mixer.Channel(_AMBIENT_CHANNEL)
        self._ambient_sound: pygame.mixer.Sound | None = None

        # SE チャンネルプール（ラウンドロビン）
        self._se_channels = [pygame.mixer.Channel(i) for i in range(_SE_CHANNEL_START, _SE_CHANNEL_END + 1)]
        self._se_rr_index = 0

    # ------------------------------------------------------------------
    # シーン切替
    # ------------------------------------------------------------------

    def apply_scene(self, scene: Scene, carry_over: bool = False) -> None:
        """シーンのオーディオ設定を反映する"""
        self._duck_settings = scene.duck_on_se

        bgm_layer = next((l for l in scene.audio_layers if l.type.value == "bgm"), None)
        ambient_layer = next((l for l in scene.audio_layers if l.type.value == "ambient"), None)

        if not carry_over:
            self._play_bgm(bgm_layer)
            self._play_ambient(ambient_layer)
        else:
            # carry_over: 前シーンの音声をそのまま引き継ぐ（音量だけ更新）
            if bgm_layer:
                self._bgm_base_vol = bgm_layer.volume
                pygame.mixer.music.set_volume(self._vol.effective_bgm() * self._bgm_base_vol)
            if ambient_layer and self._ambient_sound:
                self._ambient_channel.set_volume(self._vol.effective_ambient() * ambient_layer.volume)

    def _play_bgm(self, layer) -> None:
        if layer is None:
            pygame.mixer.music.fadeout(500)
            self._bgm_base_vol = 1.0
            return
        try:
            pygame.mixer.music.load(layer.file)
        except Exception:
            return
        self._bgm_base_vol = layer.volume
        target_vol = self._vol.effective_bgm() * self._bgm_base_vol
        if layer.fade_in_ms > 0:
            pygame.mixer.music.set_volume(0.0)
            pygame.mixer.music.play(-1 if layer.loop else 0)
            self._fade_bgm_to(target_vol, layer.fade_in_ms)
        else:
            pygame.mixer.music.set_volume(target_vol)
            pygame.mixer.music.play(-1 if layer.loop else 0)

    def _play_ambient(self, layer) -> None:
        self._ambient_channel.stop()
        self._ambient_sound = None
        if layer is None:
            return
        try:
            sound = pygame.mixer.Sound(layer.file)
        except Exception:
            return
        self._ambient_sound = sound
        vol = self._vol.effective_ambient() * layer.volume
        self._ambient_channel.set_volume(vol)
        self._ambient_channel.play(sound, loops=-1 if layer.loop else 0)

    # ------------------------------------------------------------------
    # SE 再生
    # ------------------------------------------------------------------

    def play_se(self, file: str, volume: float = 1.0) -> None:
        try:
            sound = pygame.mixer.Sound(file)
        except Exception:
            return

        ch = self._next_se_channel()
        ch.set_volume(self._vol.effective_se() * volume)
        ch.play(sound)

        if self._duck_settings.enabled:
            self._start_ducking(sound.get_length())

    def _next_se_channel(self) -> pygame.mixer.Channel:
        ch = self._se_channels[self._se_rr_index % len(self._se_channels)]
        self._se_rr_index += 1
        return ch

    # ------------------------------------------------------------------
    # BGM ダッキング
    # ------------------------------------------------------------------

    def _start_ducking(self, se_length_sec: float) -> None:
        with self._lock:
            self._duck_count += 1
        duck_vol = self._vol.effective_bgm() * self._bgm_base_vol * self._duck_settings.duck_volume
        pygame.mixer.music.set_volume(duck_vol)

        restore_after_ms = int(se_length_sec * 1000) + self._duck_settings.restore_ms
        timer = threading.Timer(restore_after_ms / 1000.0, self._finish_ducking)
        timer.daemon = True
        timer.start()

    def _finish_ducking(self) -> None:
        with self._lock:
            self._duck_count = max(0, self._duck_count - 1)
            if self._duck_count > 0:
                return  # まだ別の SE が再生中
        self._fade_bgm_to(self._vol.effective_bgm() * self._bgm_base_vol, self._duck_settings.restore_ms)

    def _fade_bgm_to(self, target: float, duration_ms: int) -> None:
        """BGM を target 音量まで duration_ms かけてフェードする（スレッドセーフ）"""
        if duration_ms <= 0:
            pygame.mixer.music.set_volume(target)
            return
        steps = max(1, duration_ms // 20)
        current = pygame.mixer.music.get_volume()
        delta = (target - current) / steps

        def _run() -> None:
            vol = current
            for _ in range(steps):
                vol = max(0.0, min(1.0, vol + delta))
                pygame.mixer.music.set_volume(vol)
                threading.Event().wait(0.02)
            pygame.mixer.music.set_volume(target)

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    # ------------------------------------------------------------------
    # リアルタイム音量スライダー
    # ------------------------------------------------------------------

    def set_master_volume(self, value: float) -> None:
        self._vol.master = _clamp(value)
        self._apply_all_volumes()

    def set_bgm_volume(self, value: float) -> None:
        self._vol.bgm = _clamp(value)
        pygame.mixer.music.set_volume(self._vol.effective_bgm() * self._bgm_base_vol)

    def set_ambient_volume(self, value: float) -> None:
        self._vol.ambient = _clamp(value)
        if self._ambient_sound:
            self._ambient_channel.set_volume(self._vol.effective_ambient())

    def set_se_volume(self, value: float) -> None:
        self._vol.se = _clamp(value)

    def _apply_all_volumes(self) -> None:
        pygame.mixer.music.set_volume(self._vol.effective_bgm() * self._bgm_base_vol)
        if self._ambient_sound:
            self._ambient_channel.set_volume(self._vol.effective_ambient())

    # ------------------------------------------------------------------
    # 停止
    # ------------------------------------------------------------------

    def stop_all(self) -> None:
        pygame.mixer.music.stop()
        self._ambient_channel.stop()
        for ch in self._se_channels:
            ch.stop()
        self._duck_count = 0

    def quit(self) -> None:
        self.stop_all()
        pygame.mixer.quit()


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))
