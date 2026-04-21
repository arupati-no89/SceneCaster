from __future__ import annotations

import threading
from dataclasses import dataclass, field

import pygame

from src.audio.eq_processor import EqSettings, load_and_apply_eq
from src.models.scenario import Scene, DuckSettings, AudioLayer

_AMBIENT_CHANNEL = 0
_BGM_CHANNEL     = 16          # 専用BGMチャンネル（EQ処理用）
_SE_CHANNEL_START = 1
_SE_CHANNEL_END   = 15         # 1〜15 の 15ch を SE 用に確保


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
        pygame.mixer.set_num_channels(17)  # 0=ambient, 1-15=SE, 16=BGM

        self._vol = _VolumeState()
        self._bgm_base_vol: float = 1.0
        self._duck_count: int = 0
        self._duck_settings: DuckSettings = DuckSettings()
        self._lock = threading.Lock()

        self._eq = EqSettings()

        self._bgm_channel  = pygame.mixer.Channel(_BGM_CHANNEL)
        self._bgm_sound: pygame.mixer.Sound | None = None
        self._current_bgm_layer: AudioLayer | None = None

        self._ambient_channel = pygame.mixer.Channel(_AMBIENT_CHANNEL)
        self._ambient_sound: pygame.mixer.Sound | None = None
        self._current_ambient_layer: AudioLayer | None = None

        self._se_channels = [pygame.mixer.Channel(i) for i in range(_SE_CHANNEL_START, _SE_CHANNEL_END + 1)]
        self._se_rr_index = 0

    # ------------------------------------------------------------------
    # シーン切替
    # ------------------------------------------------------------------

    def apply_scene(self, scene: Scene, carry_over: bool = False) -> None:
        self._duck_settings = scene.duck_on_se

        bgm_layer     = next((l for l in scene.audio_layers if l.type.value == "bgm"), None)
        ambient_layer = next((l for l in scene.audio_layers if l.type.value == "ambient"), None)

        if not carry_over:
            self._play_bgm(bgm_layer)
            self._play_ambient(ambient_layer)
        else:
            if bgm_layer:
                self._bgm_base_vol = bgm_layer.volume
                self._bgm_channel.set_volume(self._vol.effective_bgm() * self._bgm_base_vol)
            if ambient_layer and self._ambient_sound:
                self._ambient_channel.set_volume(self._vol.effective_ambient() * ambient_layer.volume)

    def _play_bgm(self, layer: AudioLayer | None) -> None:
        self._current_bgm_layer = layer
        if layer is None:
            self._bgm_channel.fadeout(500)
            self._bgm_sound = None
            self._bgm_base_vol = 1.0
            return
        try:
            sound = load_and_apply_eq(layer.file, self._eq)
        except Exception:
            return
        self._bgm_sound = sound
        self._bgm_base_vol = layer.volume
        target_vol = self._vol.effective_bgm() * self._bgm_base_vol
        if layer.fade_in_ms > 0:
            self._bgm_channel.set_volume(0.0)
            self._bgm_channel.play(sound, loops=-1 if layer.loop else 0)
            self._fade_bgm_to(target_vol, layer.fade_in_ms)
        else:
            self._bgm_channel.set_volume(target_vol)
            self._bgm_channel.play(sound, loops=-1 if layer.loop else 0)

    def _play_ambient(self, layer: AudioLayer | None) -> None:
        self._current_ambient_layer = layer
        self._ambient_channel.stop()
        self._ambient_sound = None
        if layer is None:
            return
        try:
            sound = load_and_apply_eq(layer.file, self._eq)
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
            sound = load_and_apply_eq(file, self._eq)
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
        self._bgm_channel.set_volume(duck_vol)

        restore_after_ms = int(se_length_sec * 1000) + self._duck_settings.restore_ms
        timer = threading.Timer(restore_after_ms / 1000.0, self._finish_ducking)
        timer.daemon = True
        timer.start()

    def _finish_ducking(self) -> None:
        with self._lock:
            self._duck_count = max(0, self._duck_count - 1)
            if self._duck_count > 0:
                return
        self._fade_bgm_to(self._vol.effective_bgm() * self._bgm_base_vol, self._duck_settings.restore_ms)

    def _fade_bgm_to(self, target: float, duration_ms: int) -> None:
        if duration_ms <= 0:
            self._bgm_channel.set_volume(target)
            return
        steps = max(1, duration_ms // 20)
        current = self._bgm_channel.get_volume()
        delta = (target - current) / steps

        def _run() -> None:
            vol = current
            for _ in range(steps):
                vol = max(0.0, min(1.0, vol + delta))
                self._bgm_channel.set_volume(vol)
                threading.Event().wait(0.02)
            self._bgm_channel.set_volume(target)

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
        self._bgm_channel.set_volume(self._vol.effective_bgm() * self._bgm_base_vol)

    def set_ambient_volume(self, value: float) -> None:
        self._vol.ambient = _clamp(value)
        if self._ambient_sound:
            self._ambient_channel.set_volume(self._vol.effective_ambient())

    def set_se_volume(self, value: float) -> None:
        self._vol.se = _clamp(value)

    def _apply_all_volumes(self) -> None:
        self._bgm_channel.set_volume(self._vol.effective_bgm() * self._bgm_base_vol)
        if self._ambient_sound:
            self._ambient_channel.set_volume(self._vol.effective_ambient())

    # ------------------------------------------------------------------
    # EQ
    # ------------------------------------------------------------------

    def set_eq_bass(self, db: float) -> None:
        self._eq.bass_db = _clamp_db(db)
        self._reload_audio_with_eq()

    def set_eq_mid(self, db: float) -> None:
        self._eq.mid_db = _clamp_db(db)
        self._reload_audio_with_eq()

    def set_eq_treble(self, db: float) -> None:
        self._eq.treble_db = _clamp_db(db)
        self._reload_audio_with_eq()

    def _reload_audio_with_eq(self) -> None:
        """現在再生中の BGM・環境音を EQ 設定で再ロードする。"""
        if self._current_bgm_layer is not None:
            self._play_bgm(self._current_bgm_layer)
        if self._current_ambient_layer is not None:
            self._play_ambient(self._current_ambient_layer)

    # ------------------------------------------------------------------
    # 停止
    # ------------------------------------------------------------------

    def stop_all(self) -> None:
        self._bgm_channel.stop()
        self._ambient_channel.stop()
        for ch in self._se_channels:
            ch.stop()
        self._duck_count = 0

    def quit(self) -> None:
        self.stop_all()
        pygame.mixer.quit()


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def _clamp_db(v: float) -> float:
    return max(-12.0, min(12.0, v))
