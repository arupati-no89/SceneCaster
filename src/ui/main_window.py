from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QKeyEvent, QGuiApplication
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QComboBox, QFileDialog,
    QSplitter, QGroupBox, QSizePolicy, QMessageBox,
)

from src.audio.engine import AudioEngine
from src.input.presenter import PresenterHandler
from src.models.loader import load_scenario
from src.models.scenario import Scenario, Scene
from src.ui.projection_window import ProjectionWindow
from src.ui.widgets.scene_list import SceneListWidget
from src.ui.widgets.se_pad import SePadWidget
from src.ui.widgets.eq_panel import EqPanelWidget
from src.ui.widgets.volume_panel import VolumePanelWidget

PREVIEW_SIZE = QSize(320, 180)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SceneCaster — GM Control")
        self.setMinimumSize(1100, 680)

        self._scenario: Scenario | None = None
        self._current_index: int = -1

        self._projection = ProjectionWindow()
        self._audio = AudioEngine()
        self._presenter = PresenterHandler(self)

        self._presenter.next_scene.connect(self._go_next)
        self._presenter.prev_scene.connect(self._go_prev)
        self._presenter.blackout.connect(self._toggle_blackout)

        # 投影ウィンドウにフォーカスがあってもキーを処理できるよう転送
        self._projection.key_pressed.connect(self._presenter.handle_key)

        self._build_ui()

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        splitter.addWidget(self._build_left_pane())
        splitter.addWidget(self._build_center_pane())
        splitter.addWidget(self._build_right_pane())
        splitter.setSizes([200, 480, 320])

    # ---- 左ペイン: シーンリスト ----

    def _build_left_pane(self) -> QWidget:
        pane = QWidget()
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(0, 0, 0, 0)

        load_group = QGroupBox("シナリオ")
        load_layout = QVBoxLayout(load_group)
        self._btn_load = QPushButton("シナリオを開く…")
        self._btn_load.clicked.connect(self._on_load_scenario)
        self._lbl_scenario = QLabel("（未読込）")
        self._lbl_scenario.setWordWrap(True)
        load_layout.addWidget(self._btn_load)
        load_layout.addWidget(self._lbl_scenario)
        layout.addWidget(load_group)

        layout.addWidget(QLabel("シーン一覧"))
        self._scene_list = SceneListWidget()
        self._scene_list.scene_selected.connect(self._on_scene_selected)
        layout.addWidget(self._scene_list)
        return pane

    # ---- 中央ペイン: プレビュー + ナビ + 音量 ----

    def _build_center_pane(self) -> QWidget:
        pane = QWidget()
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # プレビュー
        preview_group = QGroupBox("現在のシーン")
        preview_layout = QVBoxLayout(preview_group)
        self._preview_label = QLabel()
        self._preview_label.setFixedSize(PREVIEW_SIZE)
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setStyleSheet("background: #111; border: 1px solid #444;")
        self._lbl_scene_title = QLabel("—")
        self._lbl_scene_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self._preview_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        preview_layout.addWidget(self._lbl_scene_title)
        layout.addWidget(preview_group)

        # シーン送り / 戻し
        nav_layout = QHBoxLayout()
        self._btn_prev = QPushButton("◀ 前のシーン  [←]")
        self._btn_prev.clicked.connect(self._go_prev)
        self._btn_next = QPushButton("次のシーン ▶  [→]")
        self._btn_next.clicked.connect(self._go_next)
        nav_layout.addWidget(self._btn_prev)
        nav_layout.addWidget(self._btn_next)
        layout.addLayout(nav_layout)

        # ブラックアウト
        self._btn_blackout = QPushButton("● ブラックアウト  [B]")
        self._btn_blackout.setCheckable(True)
        self._btn_blackout.clicked.connect(self._on_blackout_toggled)
        layout.addWidget(self._btn_blackout)

        # 音量パネル
        self._volume_panel = VolumePanelWidget()
        self._volume_panel.master_changed.connect(self._audio.set_master_volume)
        self._volume_panel.bgm_changed.connect(self._audio.set_bgm_volume)
        self._volume_panel.ambient_changed.connect(self._audio.set_ambient_volume)
        self._volume_panel.se_changed.connect(self._audio.set_se_volume)
        layout.addWidget(self._volume_panel)

        # EQ パネル
        self._eq_panel = EqPanelWidget()
        self._eq_panel.bass_changed.connect(self._audio.set_eq_bass)
        self._eq_panel.mid_changed.connect(self._audio.set_eq_mid)
        self._eq_panel.treble_changed.connect(self._audio.set_eq_treble)
        layout.addWidget(self._eq_panel)

        layout.addStretch()
        return pane

    # ---- 右ペイン: SE パッド + 投影設定 ----

    def _build_right_pane(self) -> QWidget:
        pane = QWidget()
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # SE パッド
        self._se_pad = SePadWidget()
        self._se_pad.se_triggered.connect(self._audio.play_se)
        layout.addWidget(self._se_pad, stretch=1)

        # 投影設定
        proj_group = QGroupBox("投影先ディスプレイ")
        proj_layout = QVBoxLayout(proj_group)
        self._screen_combo = QComboBox()
        self._refresh_screen_list()
        proj_layout.addWidget(self._screen_combo)

        btn_show_proj = QPushButton("投影ウィンドウを表示")
        btn_show_proj.clicked.connect(self._show_projection)
        btn_fullscreen = QPushButton("フルスクリーン切替  [F]")
        btn_fullscreen.clicked.connect(self._projection.toggle_fullscreen)
        proj_layout.addWidget(btn_show_proj)
        proj_layout.addWidget(btn_fullscreen)
        layout.addWidget(proj_group)
        return pane

    # ------------------------------------------------------------------
    # シナリオ操作
    # ------------------------------------------------------------------

    def _on_load_scenario(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "シナリオフォルダを選択")
        if not folder:
            return
        try:
            scenario = load_scenario(folder, resolve_assets=False)
        except (FileNotFoundError, ValueError) as e:
            QMessageBox.critical(self, "読込エラー", str(e))
            return

        self._scenario = scenario
        self._lbl_scenario.setText(f"『{scenario.title}』\n{len(scenario.scenes)} シーン")
        self._scene_list.load_scenes(scenario.scenes)
        self._on_scene_selected(0)

    def _on_scene_selected(self, index: int) -> None:
        if self._scenario is None or index < 0:
            return
        self._current_index = index
        scene = self._scenario.scenes[index]
        self._lbl_scene_title.setText(f"[{index + 1}/{len(self._scenario.scenes)}]  {scene.title}")
        self._update_preview(scene)
        self._projection.transition_to(scene.image, scene.fade_ms)
        self._audio.apply_scene(scene, carry_over=scene.carry_over_audio)
        self._se_pad.load_buttons(
            self._scenario.shared_se,
            scene.scene_specific_se,
        )

    def _go_next(self) -> None:
        if self._scenario is None:
            return
        next_idx = self._current_index + 1
        if next_idx < len(self._scenario.scenes):
            self._scene_list.select_scene(next_idx)
            self._on_scene_selected(next_idx)

    def _go_prev(self) -> None:
        if self._scenario is None:
            return
        prev_idx = self._current_index - 1
        if prev_idx >= 0:
            self._scene_list.select_scene(prev_idx)
            self._on_scene_selected(prev_idx)

    def _toggle_blackout(self) -> None:
        new_state = not self._projection.is_blackout
        self._projection.set_blackout(new_state)
        self._btn_blackout.setChecked(new_state)
        self._btn_blackout.setText(
            "○ ブラックアウト解除  [B]" if new_state else "● ブラックアウト  [B]"
        )

    def _on_blackout_toggled(self, checked: bool) -> None:
        self._projection.set_blackout(checked)
        self._btn_blackout.setText(
            "○ ブラックアウト解除  [B]" if checked else "● ブラックアウト  [B]"
        )

    # ------------------------------------------------------------------
    # キー入力（プレゼンター含む）
    # ------------------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if self._presenter.handle_key(event):
            return
        key = Qt.Key(event.key())
        if key == Qt.Key.Key_F:
            self._projection.toggle_fullscreen()
        else:
            super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # ディスプレイ管理
    # ------------------------------------------------------------------

    def _refresh_screen_list(self) -> None:
        self._screen_combo.clear()
        for i, screen in enumerate(QGuiApplication.screens()):
            label = f"画面 {i + 1}: {screen.name()}  ({screen.size().width()}×{screen.size().height()})"
            self._screen_combo.addItem(label)
        if self._screen_combo.count() > 1:
            self._screen_combo.setCurrentIndex(1)

    def _show_projection(self) -> None:
        screens = QGuiApplication.screens()
        idx = self._screen_combo.currentIndex()
        screen = screens[idx] if 0 <= idx < len(screens) else screens[0]
        if idx > 0:
            self._projection.show_fullscreen_on(screen)
        else:
            self._projection.setGeometry(screen.geometry())
            self._projection.show()

    # ------------------------------------------------------------------
    # プレビュー
    # ------------------------------------------------------------------

    def _update_preview(self, scene: Scene) -> None:
        if scene.image:
            px = QPixmap(scene.image)
            if not px.isNull():
                self._preview_label.setPixmap(
                    px.scaled(PREVIEW_SIZE, Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
                )
                self._preview_label.setText("")
                return
        self._preview_label.setPixmap(QPixmap())
        self._preview_label.setText("（画像なし）")

    # ------------------------------------------------------------------
    # 終了処理
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802
        self._audio.quit()
        self._projection.close()
        super().closeEvent(event)
