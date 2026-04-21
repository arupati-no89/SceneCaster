# SceneCaster（仮称）開発プラン

マダミス・TRPG進行補助用の、オフライン動作するBGM＋スライド再生ソフトウェア。
Windows PC上でGMが操作し、プロジェクター／外部ディスプレイへシーンごとの画像・音声を出力する。

---

## 1. プロジェクト概要

### 目的
マダミス・TRPGセッションにおいて、GM（ゲームマスター）が事前に組んだシーンを、当日はボタン一つで切り替え、BGM・環境音・効果音とスライド（画像／動画）を同期して演出するツール。

### 想定ユーザー
- シェアラボ（神戸・三宮・大阪エリアのボードゲーム／マダミスイベント運営）のGM
- 1セッション = 1シナリオ = 10〜49シーン程度

### 動作環境
- Windows 10 / 11
- **完全オフライン動作**（インターネット接続不要）
- 2画面運用（GM操作用PC画面 ＋ プロジェクター／外部ディスプレイへの投影）

---

## 2. 要件定義（確定事項）

### 2.1 画面構成
- **GM操作用ウィンドウ**と**投影用ウィンドウ**の2ウィンドウ構成
- 投影ウィンドウは**フルスクリーン／ウィンドウモード両対応**、物理ディスプレイの選択が可能
- GM操作ウィンドウでシーン選択・音量調整・SE発火を行う

### 2.2 シーン管理
- 1シナリオあたり想定シーン数：**10〜49**
- シーン切替は**手動ボタン操作**が基本
- **Bluetoothプレゼンター対応**（コクヨ フィンガープレゼンター ELA-FP1）
  - HIDキーボードとしてOSに認識されるため、`keyPressEvent`でPageDown／PageUp等をフック
  - 必須対応キー：次シーン、前シーン、ブラックアウト（Bキー相当）
- **シーン遷移時のクロスフェード**をシーンごとに設定可能（ms単位）
  - 画像／動画のフェード
  - BGM・環境音のフェード（独立設定可）

### 2.3 オーディオ（マルチレイヤー構成）
- **BGMレーン**：ループ再生、フェードイン／アウト対応
- **環境音レーン**：BGMと独立してループ再生
- **効果音（SE）レーン**：ワンショット再生、複数チャンネル同時発火可能
- **SE発火時のBGM自動ダッキング**（シーンごとに有効／無効＆減衰量を設定可能）
- **本番中のリアルタイム音量スライダー**
  - マスター音量
  - BGM音量
  - 環境音音量
  - SE音量

### 2.4 ビジュアル
- **画像表示**：必須（JPEG, PNG）
- **動画表示**：オプション（mp4対応で十分）
- **ブラックアウト機能**：投影画面を一時的に黒塗り（GM離席時等）

### 2.5 データ保存・配布
- 1シナリオ = 1フォルダ構成（`scenario.json` ＋ `assets/` サブディレクトリ）
- 他GMへの配布機能は将来検討（現時点ではzip手動配布で十分）

### 2.6 配布形式
- PyInstallerによるexe化（魚住のCAD検索ツール・AR Overlayと同スタック）

---

## 3. 技術スタック

| 領域 | 採用ライブラリ | 理由 |
|---|---|---|
| GUI | **PySide6** | 2画面運用・クロスフェード・リアルタイムスライダーに最適 |
| オーディオ | **pygame.mixer** | BGM／環境音／SEのレーン分離が自然、フェード・ループ標準装備 |
| 動画再生 | **python-vlc**（導入時） | コーデック問題が少ない、mp4確実再生 |
| 画像処理 | **Pillow** | 既存実績あり |
| データ | **JSON**（標準ライブラリ） | 手書き編集・zip配布に向く |
| exe化 | **PyInstaller** | 既存実績あり |

### ライブラリ注意点
- **pygame.mixer**はPySide6と同一プロセスで共存可能。`pygame.init()`は呼ばず、`pygame.mixer.init()`のみ呼ぶこと
- **SEチャンネル数**は`pygame.mixer.set_num_channels(16)`で余裕を持って確保
- **python-vlc**採用時は、PyInstallerの`--add-data`でVLCランタイム（dll、pluginsフォルダ）を同梱する必要あり

---

## 4. アーキテクチャ

```
┌─ MainWindow (GM操作用) ──────────────────────────┐
│  ├─ シーンリスト（左ペイン、10〜49行）            │
│  ├─ 現在シーンのプレビュー（中央上部）             │
│  ├─ 音量スライダー群（中央下部）                   │
│  │   ・マスター / BGM / 環境音 / SE              │
│  ├─ SEワンショットボタンパッド（右ペイン）         │
│  ├─ シーン送り／戻しボタン                        │
│  ├─ ブラックアウトトグル                          │
│  └─ シナリオ読込ボタン                            │
└────────────────────────────────────────────────┘
                │
                ▼
┌─ ProjectionWindow (投影用) ──────────────────────┐
│  画像／動画のみ表示                                │
│  クロスフェード付きで切替                          │
│  選択した物理ディスプレイにフルスクリーン表示       │
│  （ウィンドウモード切替可）                        │
└────────────────────────────────────────────────┘

┌─ AudioEngine (pygame.mixer) ──────────────────────┐
│  ├─ BGMレーン（pygame.mixer.music）              │
│  │   ループ／フェード／ダッキング対象              │
│  ├─ 環境音レーン（Channel 0）                    │
│  │   ループ／独立音量                             │
│  └─ SEチャンネル群（Channel 1〜15）               │
│      ワンショット／ダッキング発火源                │
└────────────────────────────────────────────────┘

┌─ InputHandler ───────────────────────────────────┐
│  ├─ GUIボタンクリック                             │
│  ├─ キーボードショートカット                       │
│  └─ Bluetoothプレゼンター入力（HIDキーイベント）  │
└────────────────────────────────────────────────┘
```

---

## 5. データスキーマ

### 5.1 ディレクトリ構造

```
MyScenario/
├── scenario.json          # シナリオ全体定義
├── assets/
│   ├── images/
│   │   ├── opening.jpg
│   │   └── library.jpg
│   ├── videos/
│   │   └── ending.mp4
│   └── audio/
│       ├── bgm_tension.ogg
│       ├── ambient_rain.ogg
│       └── se_door.wav
└── README.txt（オプション）
```

### 5.2 scenario.json スキーマ（叩き台）

```json
{
  "schema_version": "1.0",
  "title": "シナリオタイトル",
  "author": "作者名",
  "description": "シナリオ概要",
  "default_fade_ms": 1500,
  "shared_se": [
    {"id": "door_open", "label": "扉を開ける", "file": "assets/audio/se_door.wav", "volume": 0.8},
    {"id": "scream",    "label": "悲鳴",       "file": "assets/audio/se_scream.wav", "volume": 1.0}
  ],
  "scenes": [
    {
      "scene_id": "01_opening",
      "title": "プロローグ",
      "image": "assets/images/opening.jpg",
      "video": null,
      "fade_ms": 2000,
      "audio_layers": [
        {
          "type": "bgm",
          "file": "assets/audio/bgm_opening.ogg",
          "volume": 0.7,
          "loop": true,
          "fade_in_ms": 3000
        }
      ],
      "duck_on_se": {
        "enabled": true,
        "duck_volume": 0.3,
        "restore_ms": 500
      },
      "carry_over_audio": false,
      "scene_specific_se": []
    },
    {
      "scene_id": "03_investigation",
      "title": "証拠集めの時間",
      "image": "assets/images/library.jpg",
      "video": null,
      "fade_ms": 1500,
      "audio_layers": [
        {
          "type": "bgm",
          "file": "assets/audio/bgm_tension.ogg",
          "volume": 0.6,
          "loop": true,
          "fade_in_ms": 2000
        },
        {
          "type": "ambient",
          "file": "assets/audio/ambient_rain.ogg",
          "volume": 0.3,
          "loop": true,
          "fade_in_ms": 2000
        }
      ],
      "duck_on_se": {"enabled": true, "duck_volume": 0.3, "restore_ms": 500},
      "carry_over_audio": false,
      "scene_specific_se": [
        {"id": "clue_found", "label": "手がかり発見", "file": "assets/audio/se_chime.wav", "volume": 0.9}
      ]
    }
  ]
}
```

### 5.3 フィールド解説

| フィールド | 説明 |
|---|---|
| `fade_ms` | このシーンへ遷移する際のクロスフェード時間（ms） |
| `audio_layers` | 同時再生するオーディオレイヤーの配列。`type`は`bgm`／`ambient` |
| `duck_on_se` | SE発火時にBGM音量を一時的に下げる設定 |
| `carry_over_audio` | `true`の場合、前シーンの音声を引き継ぐ（章またぎ用） |
| `shared_se` | 全シーンで使える共通SEボタン（扉、悲鳴など汎用音） |
| `scene_specific_se` | このシーンでのみ使うSEボタン（シナリオ固有音） |

---

## 6. 実装順序（推奨）

> **凡例：** ✅ 完了　🔧 実装中　📋 未着手

### Phase 1: データ構造とファイルI/O ✅ 完了
1. ✅ `scenario.json`スキーマ確定（Pydanticモデルで型定義推奨）→ `src/models/scenario.py`
2. ✅ サンプルシナリオデータの作成 → `sample_scenarios/tutorial/scenario.json`
3. ✅ JSON読み込み・バリデーション → `src/models/loader.py`

### Phase 2: 基本GUI ✅ 完了
4. ✅ PySide6でMainWindow雛形 → `src/ui/main_window.py`
5. ✅ ProjectionWindow雛形＋物理ディスプレイ選択 → `src/ui/projection_window.py`
6. ✅ フルスクリーン／ウィンドウモード切替
7. ✅ シーンリスト表示・選択 → `src/ui/widgets/scene_list.py`

### Phase 3: ビジュアル演出 ✅ 完了
8. ✅ 画像表示（`QLabel` + `QPixmap`）
9. ✅ クロスフェード実装（`QGraphicsOpacityEffect` + `QPropertyAnimation`）→ `src/utils/fade.py`
10. ✅ ブラックアウト機能（フェードイン／アウト付き）

### Phase 4: オーディオエンジン ✅ 完了
11. ✅ pygame.mixer初期化＆マルチチャンネル構成 → `src/audio/engine.py`
12. ✅ BGMレーン（ループ・フェード）
13. ✅ 環境音レーン
14. ✅ SEワンショット再生
15. ✅ BGM自動ダッキング実装（カウンタ方式で複数SE重複対応）

### Phase 5: リアルタイム操作 ✅ 完了
16. ✅ 音量スライダー実装（マスター／BGM／環境音／SE）→ `src/ui/widgets/volume_panel.py`
17. ✅ SEワンショットボタンパッド（共通SE・シーン固有SE色分け）→ `src/ui/widgets/se_pad.py`
18. ✅ キーボードショートカット対応（←→ / PageUp/Down / B / F）
19. 📋 Bluetoothプレゼンター対応確認（ELA-FP1実機テスト）→ `src/input/presenter.py` 実装済み・実機検証待ち

### Phase 6: 動画対応（オプション）📋 未着手
20. 📋 python-vlc統合
21. 📋 動画クロスフェード

### Phase 7: 仕上げ 📋 未着手
22. ✅ シナリオ読込UI（フォルダ選択ダイアログ実装済み）
23. 📋 エラーハンドリング（アセット不在・JSON不正の通知強化）
24. 📋 PyInstallerでexe化

---

## 7. 補足事項・実装時の要注意ポイント

### 7.1 Bluetoothプレゼンター（ELA-FP1）
- OSからはHIDキーボードとして認識される
- 一般的に送出されるキー：PageDown / PageUp / F5 / B（ブラックアウト）/ Esc
- **実機テストで正確なキーコードを確認すること**（メモ帳等に入力して確認）
- フォーカスが投影ウィンドウにあっても、GM操作ウィンドウにあっても両方でキーを拾える設計にする

### 7.2 2画面運用の実装ポイント
```python
from PySide6.QtGui import QGuiApplication

screens = QGuiApplication.screens()
# screens[0] = プライマリ（GM操作）
# screens[1] = セカンダリ（投影先）
projection_window.setGeometry(screens[1].geometry())
projection_window.showFullScreen()
```

### 7.3 pygame.mixer初期化
```python
import pygame
# pygame.init() は呼ばない（QtのイベントループとSDL2が競合する可能性）
pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
pygame.mixer.init()
pygame.mixer.set_num_channels(16)
```

### 7.4 ダッキング実装の方針
- SE再生時：`pygame.mixer.music.set_volume(bgm_base_volume * duck_ratio)`
- SE長さを取得：`Sound.get_length()`
- 復帰：`QTimer.singleShot(int(se_length * 1000) + restore_ms, restore_bgm)`
- **複数SEが重なった場合のダッキング管理**：カウンタ方式で「現在再生中のSE数」を追跡し、0になったら復帰

### 7.5 PyInstaller（VLC同梱時）
```bash
pyinstaller --onefile --windowed \
  --add-data "path/to/vlc/libvlc.dll;." \
  --add-data "path/to/vlc/libvlccore.dll;." \
  --add-data "path/to/vlc/plugins;plugins" \
  main.py
```

---

## 8. 未決事項・今後の検討

- [ ] SEボタンのレイアウト（固定グリッド／カスタマイズ可）
- [ ] シナリオ編集機能をアプリ内に持つか、JSON手動編集で済ませるか
- [ ] シーン進行ログの記録機能（何時何分にどのシーンを発動したか）
- [ ] プレイリスト的な複数シナリオ連続実行
- [ ] キーボードショートカット一覧のUI表示
- [ ] シーン間のプリロード（切替時のラグ低減）

---

## 9. プロジェクト名候補

現在の仮称：**SceneCaster**

他案：
- **TableStage**（卓上演出）
- **SessionDirector**
- **演卓 / Entaku**（演出＋卓上の合成）
- **GMStage**

本実装開始前に正式名を決定する。

---

## 10. リポジトリ初期構成（提案）

```
scenecaster/
├── README.md
├── requirements.txt
├── main.py
├── src/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── scenario.py        # Pydanticモデル
│   ├── audio/
│   │   ├── __init__.py
│   │   └── engine.py          # pygame.mixerラッパー
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   ├── projection_window.py
│   │   └── widgets/
│   │       ├── scene_list.py
│   │       ├── volume_panel.py
│   │       └── se_pad.py
│   ├── input/
│   │   ├── __init__.py
│   │   └── presenter.py       # HIDキーイベント処理
│   └── utils/
│       └── fade.py            # フェードアニメヘルパー
├── sample_scenarios/
│   └── tutorial/
│       ├── scenario.json
│       └── assets/
└── tests/
    └── test_scenario_loader.py
```

---

## 参考：開発者プロフィール
- 魚住太郎（シェアラボ運営）
- Python経験あり（PyInstaller／Tkinter／OpenCV／Pillowの実装経験）
- AR Character Overlay（Python）、CAD検索ツール（Python/tkinter v1.0-v5.0）の開発経験
