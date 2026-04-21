# SceneCaster

マダミス・TRPG セッション進行補助ツール。  
GM が事前に組んだシーンを当日ボタン一つで切り替え、BGM・環境音・効果音とスライド画像を同期して演出します。

## 特徴

- **2画面運用** — GM 操作ウィンドウ ＋ プロジェクター／外部ディスプレイへの投影ウィンドウ
- **クロスフェード切替** — シーンごとにフェード時間（ms）を設定可能
- **マルチレイヤーオーディオ** — BGM・環境音・SE を独立レーンで制御
- **BGM 自動ダッキング** — SE 発火時に BGM を自動的に下げ、終了後に復帰
- **リアルタイム音量スライダー** — マスター / BGM / 環境音 / SE を本番中に調整
- **Bluetooth プレゼンター対応** — コクヨ ELA-FP1（HID キーボード）でシーン送り
- **完全オフライン動作** — インターネット接続不要
- **PyInstaller exe 配布** — Python 環境不要で配布可能（予定）

## 動作環境

- Windows 10 / 11
- Python 3.11 以上

## インストール

```bash
pip install -r requirements.txt
```

## 起動

```bash
python main.py
```

## シナリオの作り方

```
MyScenario/
├── scenario.json
└── assets/
    ├── images/   # JPEG, PNG
    ├── audio/    # OGG, WAV
    └── videos/   # MP4（オプション）
```

`sample_scenarios/tutorial/` にサンプルとスキーマ解説があります。  
`scenario.json` の詳細は [SceneCaster_Plan.md](SceneCaster_Plan.md) の §5 を参照してください。

## キーボードショートカット

| キー | 操作 |
|---|---|
| `→` / `PageDown` | 次のシーン |
| `←` / `PageUp` | 前のシーン |
| `B` | ブラックアウト切替 |
| `F` | フルスクリーン切替 |

## 開発状況

| フェーズ | 内容 | 状態 |
|---|---|---|
| Phase 1 | データモデル・JSON I/O | ✅ 完了 |
| Phase 2 | 基本 GUI（2画面・シーン管理） | ✅ 完了 |
| Phase 3 | クロスフェード・ブラックアウト | ✅ 完了 |
| Phase 4 | オーディオエンジン | ✅ 完了 |
| Phase 5 | 音量スライダー・SE パッド・入力 | ✅ 完了 |
| Phase 6 | 動画対応（python-vlc） | 📋 予定 |
| Phase 7 | exe 化・エラーハンドリング | 📋 予定 |

## 技術スタック

| 領域 | ライブラリ |
|---|---|
| GUI | PySide6 |
| オーディオ | pygame.mixer |
| 動画（予定） | python-vlc |
| データモデル | Pydantic v2 |
| 配布 | PyInstaller |

## 開発者

魚住太郎（シェアラボ）  
Python 実績：PyInstaller / OpenCV / Pillow / tkinter
