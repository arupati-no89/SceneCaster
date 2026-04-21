import json
import pytest
from pathlib import Path

from src.models.scenario import Scenario, AudioType
from src.models.loader import load_scenario

TUTORIAL_DIR = Path(__file__).parent.parent / "sample_scenarios" / "tutorial"


def test_load_tutorial_schema_only():
    """アセット存在確認なしでスキーマだけ検証する"""
    scenario = load_scenario(TUTORIAL_DIR, resolve_assets=False)
    assert scenario.title == "チュートリアルシナリオ"
    assert len(scenario.scenes) == 5


def test_scene_ids_unique():
    scenario = load_scenario(TUTORIAL_DIR, resolve_assets=False)
    ids = [s.scene_id for s in scenario.scenes]
    assert len(ids) == len(set(ids))


def test_audio_layers_types():
    scenario = load_scenario(TUTORIAL_DIR, resolve_assets=False)
    investigation = scenario.get_scene("03_investigation")
    assert investigation is not None
    types = {layer.type for layer in investigation.audio_layers}
    assert AudioType.BGM in types
    assert AudioType.AMBIENT in types


def test_shared_se_present():
    scenario = load_scenario(TUTORIAL_DIR, resolve_assets=False)
    assert len(scenario.shared_se) == 3


def test_carry_over_audio_flag():
    scenario = load_scenario(TUTORIAL_DIR, resolve_assets=False)
    briefing = scenario.get_scene("02_briefing")
    assert briefing is not None
    assert briefing.carry_over_audio is True


def test_invalid_json_raises(tmp_path):
    (tmp_path / "scenario.json").write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON パース"):
        load_scenario(tmp_path, resolve_assets=False)


def test_missing_scene_id_raises(tmp_path):
    data = {
        "title": "test",
        "scenes": [
            {"scene_id": "s1", "title": "A", "image": "x.jpg"},
            {"scene_id": "s1", "title": "B", "image": "x.jpg"},  # 重複
        ]
    }
    (tmp_path / "scenario.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="重複"):
        load_scenario(tmp_path, resolve_assets=False)


def test_no_image_or_video_raises(tmp_path):
    data = {
        "title": "test",
        "scenes": [
            {"scene_id": "s1", "title": "A"}  # image も video もない
        ]
    }
    (tmp_path / "scenario.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_scenario(tmp_path, resolve_assets=False)
