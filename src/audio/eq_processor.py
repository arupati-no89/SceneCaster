from __future__ import annotations

from dataclasses import dataclass
from math import gcd

import numpy as np
import pygame
import soundfile as sf
from scipy.signal import lfilter, resample_poly

_MIXER_SR = 44100


@dataclass
class EqSettings:
    bass_db: float = 0.0    # low shelf  ~100 Hz
    mid_db: float = 0.0     # peaking    ~1 kHz
    treble_db: float = 0.0  # high shelf ~8 kHz

    def is_flat(self) -> bool:
        return self.bass_db == 0.0 and self.mid_db == 0.0 and self.treble_db == 0.0


def load_and_apply_eq(file: str, eq: EqSettings) -> pygame.mixer.Sound:
    """音声ファイルをロードして EQ を適用し pygame.mixer.Sound を返す。"""
    data, sr = sf.read(file, dtype="float32", always_2d=True)

    # ステレオに正規化
    if data.shape[1] == 1:
        data = np.concatenate([data, data], axis=1)
    elif data.shape[1] > 2:
        data = data[:, :2]

    # ミキサーのサンプルレートと異なる場合はリサンプル
    if sr != _MIXER_SR:
        g = gcd(_MIXER_SR, sr)
        data = resample_poly(data, _MIXER_SR // g, sr // g, axis=0).astype(np.float32)

    if not eq.is_flat():
        data = _apply_eq(data, eq)

    int_data = np.ascontiguousarray(np.clip(data, -1.0, 1.0) * 32767, dtype=np.int16)
    return pygame.sndarray.make_sound(int_data)


def _apply_eq(samples: np.ndarray, eq: EqSettings) -> np.ndarray:
    result = samples.copy()
    if eq.bass_db:
        b, a = _low_shelf(_MIXER_SR, 100.0, eq.bass_db)
        result = _filt(result, b, a)
    if eq.mid_db:
        b, a = _peaking(_MIXER_SR, 1000.0, 1.5, eq.mid_db)
        result = _filt(result, b, a)
    if eq.treble_db:
        b, a = _high_shelf(_MIXER_SR, 8000.0, eq.treble_db)
        result = _filt(result, b, a)
    return result


def _filt(samples: np.ndarray, b, a) -> np.ndarray:
    out = np.empty_like(samples)
    for ch in range(samples.shape[1]):
        out[:, ch] = lfilter(b, a, samples[:, ch])
    return out


def _low_shelf(sr: int, fc: float, gain_db: float):
    """Audio EQ Cookbook — lowShelf (S=1)"""
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * np.pi * fc / sr
    cw, sw = np.cos(w0), np.sin(w0)
    sq = np.sqrt(A)
    alpha = sw / 2 * np.sqrt(2)   # S=1 → (1/S−1)=0 → α = sin(w0)/2·√2

    b0 =     A * ((A+1) - (A-1)*cw + 2*sq*alpha)
    b1 =  2*A * ((A-1) - (A+1)*cw)
    b2 =     A * ((A+1) - (A-1)*cw - 2*sq*alpha)
    a0 =          (A+1) + (A-1)*cw + 2*sq*alpha
    a1 =    -2 * ((A-1) + (A+1)*cw)
    a2 =          (A+1) + (A-1)*cw - 2*sq*alpha
    return np.array([b0, b1, b2]) / a0, np.array([1.0, a1/a0, a2/a0])


def _high_shelf(sr: int, fc: float, gain_db: float):
    """Audio EQ Cookbook — highShelf (S=1)"""
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * np.pi * fc / sr
    cw, sw = np.cos(w0), np.sin(w0)
    sq = np.sqrt(A)
    alpha = sw / 2 * np.sqrt(2)   # S=1

    b0 =     A * ((A+1) + (A-1)*cw + 2*sq*alpha)
    b1 = -2*A * ((A-1) + (A+1)*cw)
    b2 =     A * ((A+1) + (A-1)*cw - 2*sq*alpha)
    a0 =          (A+1) - (A-1)*cw + 2*sq*alpha
    a1 =      2 * ((A-1) - (A+1)*cw)
    a2 =          (A+1) - (A-1)*cw - 2*sq*alpha
    return np.array([b0, b1, b2]) / a0, np.array([1.0, a1/a0, a2/a0])


def _peaking(sr: int, fc: float, Q: float, gain_db: float):
    """Audio EQ Cookbook — peakingEQ"""
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * np.pi * fc / sr
    alpha = np.sin(w0) / (2 * Q)
    cw = np.cos(w0)

    b0 =  1 + alpha * A
    b1 = -2 * cw
    b2 =  1 - alpha * A
    a0 =  1 + alpha / A
    a1 = -2 * cw
    a2 =  1 - alpha / A
    return np.array([b0, b1, b2]) / a0, np.array([1.0, a1/a0, a2/a0])
