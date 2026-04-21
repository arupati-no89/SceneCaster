from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class AudioType(str, Enum):
    BGM = "bgm"
    AMBIENT = "ambient"


class AudioLayer(BaseModel):
    type: AudioType
    file: str
    volume: float = Field(default=1.0, ge=0.0, le=1.0)
    loop: bool = True
    fade_in_ms: int = Field(default=0, ge=0)


class DuckSettings(BaseModel):
    enabled: bool = True
    duck_volume: float = Field(default=0.3, ge=0.0, le=1.0)
    restore_ms: int = Field(default=500, ge=0)


class SeButton(BaseModel):
    id: str
    label: str
    file: str
    volume: float = Field(default=1.0, ge=0.0, le=1.0)


class Scene(BaseModel):
    scene_id: str
    title: str
    image: Optional[str] = None
    video: Optional[str] = None
    fade_ms: int = Field(default=1500, ge=0)
    audio_layers: list[AudioLayer] = Field(default_factory=list)
    duck_on_se: DuckSettings = Field(default_factory=DuckSettings)
    carry_over_audio: bool = False
    scene_specific_se: list[SeButton] = Field(default_factory=list)

    @model_validator(mode="after")
    def image_or_video_required(self) -> Scene:
        if self.image is None and self.video is None:
            raise ValueError(f"Scene '{self.scene_id}': image または video のどちらかが必要です")
        return self


class Scenario(BaseModel):
    schema_version: str = "1.0"
    title: str
    author: str = ""
    description: str = ""
    default_fade_ms: int = Field(default=1500, ge=0)
    shared_se: list[SeButton] = Field(default_factory=list)
    scenes: list[Scene] = Field(min_length=1)

    @field_validator("scenes")
    @classmethod
    def scene_ids_unique(cls, scenes: list[Scene]) -> list[Scene]:
        ids = [s.scene_id for s in scenes]
        duplicates = {sid for sid in ids if ids.count(sid) > 1}
        if duplicates:
            raise ValueError(f"scene_id が重複しています: {duplicates}")
        return scenes

    def get_scene(self, scene_id: str) -> Optional[Scene]:
        return next((s for s in self.scenes if s.scene_id == scene_id), None)

    def resolve_asset_paths(self, base_dir: Path) -> None:
        """全アセットパスをbase_dir基準の絶対パスに変換する（存在確認付き）"""
        missing: list[str] = []

        def check(rel: Optional[str]) -> Optional[str]:
            if rel is None:
                return None
            p = base_dir / rel
            if not p.exists():
                missing.append(str(p))
            return str(p)

        for se in self.shared_se:
            se.file = check(se.file) or se.file

        for scene in self.scenes:
            scene.image = check(scene.image)
            scene.video = check(scene.video)
            for layer in scene.audio_layers:
                layer.file = check(layer.file) or layer.file
            for se in scene.scene_specific_se:
                se.file = check(se.file) or se.file

        if missing:
            raise FileNotFoundError(
                f"以下のアセットファイルが見つかりません:\n" + "\n".join(f"  {p}" for p in missing)
            )
