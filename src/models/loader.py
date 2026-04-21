from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from .scenario import Scenario


def load_scenario(scenario_dir: str | Path, *, resolve_assets: bool = True) -> Scenario:
    """scenario.json を読み込み、Scenario オブジェクトを返す。

    Args:
        scenario_dir: scenario.json が置かれたフォルダパス
        resolve_assets: True の場合、全アセットパスを絶対パスに変換し存在確認を行う

    Raises:
        FileNotFoundError: scenario.json またはアセットが見つからない場合
        ValueError: JSON の構造・型が不正な場合
    """
    base = Path(scenario_dir).resolve()
    json_path = base / "scenario.json"

    if not json_path.exists():
        raise FileNotFoundError(f"scenario.json が見つかりません: {json_path}")

    try:
        raw = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"scenario.json の JSON パースに失敗しました: {e}") from e

    try:
        scenario = Scenario.model_validate(raw)
    except ValidationError as e:
        raise ValueError(f"scenario.json のバリデーションエラー:\n{e}") from e

    if resolve_assets:
        scenario.resolve_asset_paths(base)

    return scenario
