from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QKeySequence, QShortcut, QGuiApplication
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QComboBox, QFileDialog,
    QSplitter, QGroupBox, QSizePolicy, QMessageBox,
)

from src.models.scenario import Scenario, Scene
from src.models.loader import load_scenario
from src.ui.projection_window import ProjectionWindow
from src.ui.widgets.scene_list import SceneListWidget

PREVIEW_SIZE = QSize(320, 180)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SceneCaster — GM Control")
        self.setMinimumSize(900, 600)

        self._scenario: Scenario | None = None
        self._current_index: int = -1
        self._projection = ProjectionWindow()

        self._build_ui()
        self._setup_shortcuts()

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

        # 左ペイン: シーンリスト
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self._scene_list = SceneListWidget()
        self._scene_list.scene_selected.connect(self._on_scene_selected)
        left_layout.addWidget(QLabel("シーン一覧"))
        left_layout.addWidget(self._scene_list)
        splitter.addWidget(left)

        # 中央ペイン: プレビュー + 操作
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)

        # シナリオ読込
        load_group = QGroupBox("シナリオ")
        load_layout = QHBoxLayout(load_group)
        self._btn_load = QPushButton("シナリオを開く…")
        self._btn_load.clicked.connect(self._on_load_scenario)
        self._lbl_scenario = QLabel("（未読込）")
        self._lbl_scenario.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        load_layout.addWidget(self._btn_load)
        load_layout.addWidget(self._lbl_scenario)
        center_layout.addWidget(load_group)

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
        center_layout.addWidget(preview_group)

        # シーン送り / 戻し
        nav_layout = QHBoxLayout()
        self._btn_prev = QPushButton("◀ 前のシーン")
        self._btn_prev.setShortcut("Left")
        self._btn_prev.clicked.connect(self._go_prev)
        self._btn_next = QPushButton("次のシーン ▶")
        self._btn_next.setShortcut("Right")
        self._btn_next.clicked.connect(self._go_next)
        nav_layout.addWidget(self._btn_prev)
        nav_layout.addWidget(self._btn_next)
        center_layout.addLayout(nav_layout)

        # ブラックアウト
        self._btn_blackout = QPushButton("● ブラックアウト")
        self._btn_blackout.setCheckable(True)
        self._btn_blackout.clicked.connect(self._on_blackout_toggled)
        center_layout.addWidget(self._btn_blackout)

        center_layout.addStretch()
        splitter.addWidget(center)

        # 右ペイン: 投影設定
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        proj_group = QGroupBox("投影先ディスプレイ")
        proj_layout = QVBoxLayout(proj_group)
        self._screen_combo = QComboBox()
        self._refresh_screen_list()
        proj_layout.addWidget(self._screen_combo)

        btn_show_proj = QPushButton("投影ウィンドウを表示")
        btn_show_proj.clicked.connect(self._show_projection)
        btn_fullscreen = QPushButton("フルスクリーン切替 (F)")
        btn_fullscreen.clicked.connect(self._projection.toggle_fullscreen)
        proj_layout.addWidget(btn_show_proj)
        proj_layout.addWidget(btn_fullscreen)
        right_layout.addWidget(proj_group)
        right_layout.addStretch()
        splitter.addWidget(right)

        splitter.setSizes([200, 500, 200])

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("B"), self, self._projection.toggle_blackout)
        QShortcut(QKeySequence("F"), self, self._projection.toggle_fullscreen)
        QShortcut(QKeySequence(Qt.Key.Key_PageDown), self, self._go_next)
        QShortcut(QKeySequence(Qt.Key.Key_PageUp), self, self._go_prev)

    # ------------------------------------------------------------------
    # スロット
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
        self._lbl_scenario.setText(f"『{scenario.title}』  {len(scenario.scenes)} シーン")
        self._scene_list.load_scenes(scenario.scenes)
        self._on_scene_selected(0)

    def _on_scene_selected(self, index: int) -> None:
        if self._scenario is None or index < 0:
            return
        self._current_index = index
        scene = self._scenario.scenes[index]
        self._lbl_scene_title.setText(f"[{index + 1}/{len(self._scenario.scenes)}] {scene.title}")
        self._update_preview(scene)
        self._projection.transition_to(scene.image, scene.fade_ms)

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

    def _on_blackout_toggled(self, checked: bool) -> None:
        self._projection.set_blackout(checked)
        self._btn_blackout.setText("○ ブラックアウト解除" if checked else "● ブラックアウト")

    # ------------------------------------------------------------------
    # ディスプレイ管理
    # ------------------------------------------------------------------

    def _refresh_screen_list(self) -> None:
        self._screen_combo.clear()
        screens = QGuiApplication.screens()
        for i, screen in enumerate(screens):
            label = f"画面 {i + 1}: {screen.name()} ({screen.size().width()}×{screen.size().height()})"
            self._screen_combo.addItem(label)
        # デフォルトはセカンダリ（あれば）
        if len(screens) > 1:
            self._screen_combo.setCurrentIndex(1)

    def _show_projection(self) -> None:
        screens = QGuiApplication.screens()
        idx = self._screen_combo.currentIndex()
        screen = screens[idx] if 0 <= idx < len(screens) else screens[0]
        if self._screen_combo.currentIndex() > 0:
            self._projection.show_fullscreen_on(screen)
        else:
            self._projection.setGeometry(screen.geometry())
            self._projection.show()

    # ------------------------------------------------------------------
    # プレビュー更新
    # ------------------------------------------------------------------

    def _update_preview(self, scene: Scene) -> None:
        if scene.image:
            px = QPixmap(scene.image)
            if not px.isNull():
                self._preview_label.setPixmap(
                    px.scaled(PREVIEW_SIZE, Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
                )
                return
        self._preview_label.setPixmap(QPixmap())
        self._preview_label.setText("（画像なし）")
