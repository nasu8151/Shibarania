# SPDX-License-Identifier: MIT

import sys
import typing
import threading
import json
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QFrame,
    QSizePolicy,
    QGridLayout,
    QMessageBox,
    QGraphicsOpacityEffect,
    QPushButton,
)
from PyQt6.QtGui import QPalette, QColor, QDrag, QPixmap, QMouseEvent
from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
    QTimer,
    QMimeData,
    QPropertyAnimation,
    QPoint,
    QEvent,
    QUrl,
)
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from PyQt6.QtMultimedia import QSoundEffect, QMediaPlayer, QAudioOutput
import backend
from theme_manager import ThemeManager, LIGHT_THEME, DARK_THEME

try:
    from googleapiclient.errors import HttpError
except Exception:
    HttpError = Exception


class TaskWidget(QFrame):
    def __init__(self, task_data: dict, section: str):
        super().__init__()
        self.task_data = task_data
        self.section = section
        self.setObjectName("TaskCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        
        self._press_timer = QTimer(self)
        self._press_timer.setSingleShot(True)
        self._press_timer.timeout.connect(self._on_long_press)

        # ヒント矢印用タイマー
        self._hint_timer = QTimer(self)
        self._hint_timer.setSingleShot(True)
        self._hint_timer.timeout.connect(self._show_hint_arrow)
        
        # ヒント矢印機能を削除（モダン化に伴い不要と判断、または後で復活）
        self._press_feedback_timer = QTimer(self)
        self._press_feedback_timer.setSingleShot(True)
        self._press_feedback_timer.timeout.connect(self._apply_press_feedback)
        
        self._press_pos: QPoint | None = None
        self._long_pressed = False
        self._hint_label: QLabel | None = None
        self._hint_effect: QGraphicsOpacityEffect | None = None
        self._press_active = False
        self._is_focus = False
        self._focus_shadow: QGraphicsDropShadowEffect | None = None
        
        # 初期スタイル適用
        self._update_style()
        self._apply_normal_shadow()

    def _apply_normal_shadow(self):
        try:
            shadow = QGraphicsDropShadowEffect(self)
            # テーマに合わせて調整（ガイド準拠：Blur 20px）
            shadow.setBlurRadius(20)
            shadow.setOffset(0, 6)
            shadow.setColor(QColor(ThemeManager().current_theme.shadow))
            self.setGraphicsEffect(shadow)
        except Exception:
            pass

    def enterEvent(self, event):
        if not self._long_pressed and not self._is_focus:
            # ホバー時はわずかに明るく（QSSで十分機能しない場合のフォールバック）
            # ThemeManagerのget_style_sheetですでに :hover を定義しているので
            # ここでは何もしない、あるいはQSSが効かない場合に備えて手動設定する
            # QFrameはQSSの:hoverが効きにくい場合があるためここで補完
            is_dark = ThemeManager().is_dark
            bg = "#252525" if is_dark else "#FAFAFA"
            self.setStyleSheet(f"QFrame#TaskCard {{ background-color: {bg}; border: 2px solid transparent; border-radius: 14px; }}")
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self._long_pressed and not self._is_focus:
            # 元に戻す
            bg = ThemeManager().current_theme.card_bg
            self.setStyleSheet(f"QFrame#TaskCard {{ background-color: {bg}; border: 2px solid transparent; border-radius: 14px; }}")
        super().leaveEvent(event)

    def mousePressEvent(self, a0):
        if not a0:
            return
        if a0.button() == Qt.MouseButton.LeftButton:
            self._press_pos = a0.pos()
            self._long_pressed = False
            self._press_feedback_timer.start(80)
            self._press_timer.start(300)
        else:
            super().mousePressEvent(a0)

    def mouseMoveEvent(self, a0):
        if not a0 or self._press_pos is None:
            return
        if not self._long_pressed:
            if (a0.pos() - self._press_pos).manhattanLength() > 6:
                self._cancel_press()
            return
        self._start_drag()

    def mouseReleaseEvent(self, a0):
        self._cancel_press()
        super().mouseReleaseEvent(a0)

    def _apply_press_feedback(self) -> None:
        self._press_active = True
        self._update_style()

    def _on_long_press(self) -> None:
        self._long_pressed = True
        # モダンな浮き上がり効果 + 差し色背景
        try:
            accent = ThemeManager().current_theme.accent
            c = QColor(accent)
            # Alpha 25 (~10%)
            bg_color = f"rgba({c.red()}, {c.green()}, {c.blue()}, 25)"
            
            # ボーダーもアクセントにして「掴んでいる」感を出す
            self.setStyleSheet(f"QFrame#TaskCard {{ background-color: {bg_color}; border: 2px solid {accent}; border-radius: 14px; }}")

            # 影を少し強調するが、ガイドに従い控えめに（Lift Effect）
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(30)
            shadow.setOffset(0, 10)
            shadow.setColor(QColor(ThemeManager().current_theme.shadow))
            self.setGraphicsEffect(shadow)
            
            # ヒント矢印を表示（少し遅らせて）
            self._hint_timer.start(150)
            
        except Exception:
            pass

    def _show_hint_arrow(self) -> None:
        """長押し時に右側に完了を促す矢印を表示"""
        if self._hint_label is not None:
            return
        
        self._hint_label = QLabel(self)
        self._hint_label.setObjectName("HintArrow")
        
        # 矢印画像の読み込み
        base_dir = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(base_dir, "assets", "yajirushi.png")
        pix = QPixmap(img_path)
        
        if not pix.isNull():
            # 画像がある場合
            self._hint_label.setPixmap(pix)
            self._hint_label.adjustSize()
        else:
            # 画像がない場合はテキストで代用
            self._hint_label.setText("→")
            # アクセントカラーを使用
            accent = ThemeManager().current_theme.accent
            self._hint_label.setStyleSheet(f"color: {accent}; font-size: 32px; font-weight: bold; background: transparent;")
            self._hint_label.adjustSize()
            
        # 右端に配置
        margin = 16
        x = self.width() - self._hint_label.width() - margin
        y = (self.height() - self._hint_label.height()) // 2
        self._hint_label.move(x, y)
        
        # フェードインアニメーション
        self._hint_effect = QGraphicsOpacityEffect(self._hint_label)
        self._hint_label.setGraphicsEffect(self._hint_effect)
        
        anim = QPropertyAnimation(self._hint_effect, b"opacity", self)
        anim.setDuration(300)
        anim.setStartValue(0.0)
        anim.setEndValue(0.8)
        self._hint_label._anim = anim # type: ignore
        
        self._hint_label.show()
        anim.start()

    def _start_drag(self) -> None:
        mime = QMimeData()
        payload = {
            "id": self.task_data.get("id"),
            "title": self.task_data.get("title"),
            "description": self.task_data.get("description", ""),
            "from": self.section,
        }
        mime.setData("application/x-shibarania-task", json.dumps(payload).encode("utf-8"))
        
        drag = QDrag(self)
        drag.setMimeData(mime)
        
        # ドラッグ中のピクチャを作成（半透明のカード画像など）
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(self._press_pos if self._press_pos else QPoint(pixmap.width() // 2, pixmap.height() // 2))

        # ドラッグ開始時に自分自身を隠すことで「持ち上げた」感を出す
        self.hide()

        result = drag.exec(Qt.DropAction.MoveAction)
        
        # ドラッグ終了後の処理
        self._cancel_press()
        # 万が一ドロップ先で適切に処理されなかった場合（移動せずキャンセルされた場合など）は再表示
        # ただし移動成功時は refresh_ui で再描画されるため、ここではとりあえず再表示して問題ない
        self.show()
        self._apply_normal_shadow()

    def _cancel_press(self) -> None:
        self._press_timer.stop()
        self._press_feedback_timer.stop()
        self._hint_timer.stop()
        
        # ヒント表示の終了
        if self._hint_label:
            self._hint_label.hide()
            self._hint_label.deleteLater()
            self._hint_label = None
            self._hint_effect = None
        
        self._press_pos = None
        self._long_pressed = False
        self._press_active = False
        
        # ドラッグ終了後は通常のスタイルに戻す
        # フォーカスされている場合はフォーカス用のボーダーを維持
        if self._is_focus:
            # set_focus_enabledで設定されたスタイルに戻す(style polish)
            self.style().unpolish(self)
            self.style().polish(self)
            self._apply_normal_shadow()
        else:
            # 通常状態に戻す
            bg = ThemeManager().current_theme.card_bg
            # QSSのhoverなどが効くように styleSheet をクリアするか、明示的に設定
            # ここでは明示的に戻す（QSSとの競合を避けるため）
            self.setStyleSheet(f"QFrame#TaskCard {{ background-color: {bg}; border: 2px solid transparent; border-radius: 14px; }}")
            self._apply_normal_shadow()

    def set_focus_enabled(self, enabled: bool) -> None:
        self._is_focus = enabled
        self.setProperty("is_focus", enabled)
        
        # フォーカス時はアクセントカラーの枠線
        if enabled:
            accent = ThemeManager().current_theme.focus_border
            bg = ThemeManager().current_theme.card_bg
            self.setStyleSheet(f"QFrame#TaskCard {{ background-color: {bg}; border: 2px solid {accent}; border-radius: 14px; }}")
        else:
            # 通常
            bg = ThemeManager().current_theme.card_bg
            self.setStyleSheet(f"QFrame#TaskCard {{ background-color: {bg}; border: 2px solid transparent; border-radius: 14px; }}")

        self.style().unpolish(self)
        self.style().polish(self)
        
        # 子要素のラベルなども更新
        for child in self.findChildren(QLabel):
            child.setProperty("is_focus", enabled)
            child.style().unpolish(child)
            child.style().polish(child)

    def _update_style(self) -> None:
        pass # Stylesheet applied globally or via ThemeManager


class SectionWidget(QWidget):
    dropped = pyqtSignal(object, str, QPoint)  # payload, destination name, global pos

    def __init__(self, section_name: str):
        super().__init__()
        self.section_name = section_name
        self.setAcceptDrops(True)

    def dragEnterEvent(self, a0):
        if not a0:
            return
        mime = a0.mimeData()
        if not mime:
            a0.ignore()
            return
        if mime.hasFormat("application/x-shibarania-task"):
            a0.acceptProposedAction()
        else:
            a0.ignore()

    def dragMoveEvent(self, a0):
        if not a0:
            return
        mime = a0.mimeData()
        if not mime:
            a0.ignore()
            return

        if mime.hasFormat("application/x-shibarania-task"):
            a0.acceptProposedAction()
            
            # 親ウィンドウへ「覗き見（peek）」演出を依頼
            win = self.window()
            if hasattr(win, "peek_history_panel"):
                # 親ウィンドウ上でのX座標を取得
                global_pos = self.mapToGlobal(a0.position().toPoint())
                win_pos = win.mapFromGlobal(global_pos)
                x = win_pos.x()
                win_w = win.width()
                
                # 画面右側にあれば「完了ゾーン」として扱う準備
                # 右側30%くらいから反応し始める
                threshold = win_w * 0.7
                if x > threshold:
                    # 右端に近づくほど offset を大きくする (20px -> 120px)
                    offset = max(20, min(120, int((x - threshold) / 2)))
                    win.peek_history_panel(offset)
                else:
                    win.peek_history_panel(0)
        else:
            a0.ignore()
    
    def dragLeaveEvent(self, a0):
        # ドラッグが外れたら戻す
        win = self.window()
        if hasattr(win, "peek_history_panel"):
            win.peek_history_panel(0)
        super().dragLeaveEvent(a0)
    
    def dropEvent(self, a0):
        if not a0:
            return
        
        # ドロップされたらパネルを戻す
        win = self.window()
        is_completed_zone = False
        
        if hasattr(win, "peek_history_panel"):
            win.peek_history_panel(0)
            # ドロップ位置判定
            global_pos = self.mapToGlobal(a0.position().toPoint())
            win_pos = win.mapFromGlobal(global_pos)
            # 画面の6割より右なら完了扱い
            if win_pos.x() > win.width() * 0.6:
                is_completed_zone = True
             
        mime = a0.mimeData()
        if not mime:
            a0.ignore()
            return

        try:
            data = mime.data("application/x-shibarania-task")
            payload = json.loads(bytes(data.data()).decode("utf-8"))
            
            # 完了ゾーンまたは自分自身のセクション名
            destination = "完了済みのタスク" if is_completed_zone else self.section_name
            self.dropped.emit(payload, destination, self.mapToGlobal(a0.position().toPoint()))
            
            a0.acceptProposedAction()
        except Exception:
            a0.ignore()


class Shibarania(QWidget):
    # Console thread-safe requests into the UI thread
    request_add_task = pyqtSignal(str, str)
    request_delete_task = pyqtSignal(str)
    request_move_task = pyqtSignal(str, str)  # title, destination section
    request_set_tasks = pyqtSignal(list, list)  # current, done

    def dragEnterEvent(self, a0):
        if not a0:
            return
        mime = a0.mimeData()
        if not mime:
            a0.ignore()
            return
        if mime.hasFormat("application/x-shibarania-task"):
            a0.acceptProposedAction()
        else:
            a0.ignore()
            
    def dragMoveEvent(self, a0):
        if not a0:
            return
        mime = a0.mimeData()
        if not mime:
            a0.ignore()
            return
        if mime.hasFormat("application/x-shibarania-task"):
            a0.acceptProposedAction()
            
            # 右側でドラッグしていればパネルをチラ見せ
            # ここではShibarania全体での座標なので、右側の例えば30%領域に入れば完了の意思ありとみなす
            x = a0.position().x()
            if x > self.width() * 0.7:
                self.peek_history_panel(max(20, int((x - self.width() * 0.7) / 2))) # 深く入れるほど大きく出す
            else:
                self.peek_history_panel(0)
        else:
            a0.ignore()

    def dragLeaveEvent(self, a0):
        # ドラッグが外れたら戻す
        self.peek_history_panel(0)
        super().dragLeaveEvent(a0)

    def dropEvent(self, a0):
        if not a0:
            return
        self.peek_history_panel(0)
        
        mime = a0.mimeData()
        if not mime:
            a0.ignore()
            return
        
        # 右側にドロップされたら「完了」とみなす
        if a0.position().x() > self.width() * 0.6: # 判定条件：画面の6割より右
            try:
                data = mime.data("application/x-shibarania-task")
                payload = json.loads(bytes(data.data()).decode("utf-8"))
                # 完了とみなす
                self.on_task_dropped(payload, "完了済みのタスク", self.mapToGlobal(a0.position().toPoint()))
                a0.acceptProposedAction()
            except Exception:
                a0.ignore()
        else:
            # 完了エリア外であっても、元のSectionWidgetで拾われなかった場合
            # 何もしない (ignore) ことでキャンセル扱いになるか
            # あるいは「現在のタスク」に戻す処理が必要な場合もあるが、
            # SectionWidgetがdropEventを持っていないと親に伝播する。
            # 今回はSectionWidgetもacceptDropsを設定しているので、
            # 左側ならSectionWidgetが先に処理するはず。
            a0.ignore()

    def __init__(self, fullscreen: bool = False):
        super().__init__()
        self.setWindowTitle("Shibarania")
        self.setGeometry(100, 100, 800, 480)

        self.is_fullscreen = fullscreen
        self.ui_scale = 0.85 if self.is_fullscreen else 1.0
        self._focus_task_id: str | None = None

        # エッジスワイプ/メニュー用
        self._edge_press_pos: QPoint | None = None
        self._edge_mode: str | None = None  # "right" or "top"
        self._edge_swipe_distance = 0
        self._edge_hold_timer = QTimer(self)
        self._edge_hold_timer.setSingleShot(True)
        self._edge_hold_timer.timeout.connect(self._edge_hold_timeout)

        # ポップアップ表示時間（ミリ秒）
        self.popup_duration_ms: int = 4000

        # 完了時の効果音
        self._complete_sound: QSoundEffect | None = None
        self._complete_player: QMediaPlayer | None = None
        self._complete_audio: QAudioOutput | None = None
        sound_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "決定ボタンを押す1.mp3")
        self._setup_complete_sound(sound_path)

        # Google Tasklist ID（先頭のリストを利用）
        self.google_tasklist_id: typing.Optional[str] = None

        self._peek_offset = 0

        self.tasks = {
            "現在のタスク": [
                {"title": "TaskB", "description": "何らかの問題により"},
                {"title": "TaskD", "description": "Google Tasksからの読み込みに"},
                {"title": "TaskE", "description": "失敗しているようです。"},
                {"title": "TaskF", "description": "ネットワーク接続や"},
                {"title": "TaskG", "description": "認可設定を確認してください。"},
            ],
            "完了済みのタスク": [
                {"title": "TaskO", "description": " "},
            ],
        }

        # レイアウト作成
        layout = QHBoxLayout()
        if self.is_fullscreen:
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(8)

        # セクション作成
        current_section = self._create_section("現在のタスク", self.tasks["現在のタスク"])
        current_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(current_section, 2)

        self.setLayout(layout)
        
        # 完了済み履歴パネル（右端スワイプ）
        self._history_panel = SectionWidget("完了済みのタスク")
        self._history_panel.setParent(self)
        self._history_panel.entered = False # type: ignore
        # テーマ依存スタイルは _apply_theme で設定
        self._history_panel.dropped.connect(self.on_task_dropped)
        self._history_panel_layout = QVBoxLayout()
        self._history_panel_layout.setContentsMargins(12, 12, 12, 12)
        self._history_panel_layout.setSpacing(8)
        self._history_panel.setLayout(self._history_panel_layout)
        self._history_panel.hide()
        self._history_panel_timer = QTimer(self)
        self._history_panel_timer.setSingleShot(True)
        self._history_panel_timer.timeout.connect(self._hide_history_panel)

        # 上端メニュー
        self._menu_panel = QWidget(self)
        self._menu_panel.setStyleSheet("QWidget { background-color: rgba(0,0,0,160); }")
        self._menu_panel_layout = QVBoxLayout()
        self._menu_panel_layout.setContentsMargins(16, 16, 16, 16)
        self._menu_panel_layout.setSpacing(10)
        self._menu_panel.setLayout(self._menu_panel_layout)
        self._menu_panel.hide()
        self._build_menu_contents()
        
        # ドラッグ&ドロップの受け入れ（完了エリアの検出用）
        self.setAcceptDrops(True)
        
        # テーマを初期適用
        self._apply_theme()

        self.installEventFilter(self)

        # Connect signals to perform operations in the UI thread
        self.request_add_task.connect(self.add_task)
        self.request_delete_task.connect(self.delete_task)
        self.request_move_task.connect(self.move_task)
        self.request_set_tasks.connect(self._apply_google_sections)

        # Google Tasks から初期タスクを読み込み
        try:
            self._load_tasks_from_google()
        except Exception:
            # 認可未設定やネットワーク障害時などは初期データのまま表示
            pass

        # 定期同期タイマー開始（60秒間隔）
        try:
            self._start_periodic_sync(60_000)
        except Exception:
            pass

        self._update_history_panel()

    def add_task(self, title: str, description: str = "") -> bool:
        """タイトルと説明で "現在のタスク" に追加して UI を更新する。"""
        if title is None:
            return False
        t = title.strip()
        if not t:
            return False
        d = description if description is not None else ""
        if "現在のタスク" not in self.tasks or not isinstance(self.tasks["現在のタスク"], list):
            self.tasks["現在のタスク"] = []
        self.tasks["現在のタスク"].append({"title": t, "description": d})
        try:
            self.refresh_ui()
        except Exception:
            pass
        return True

    def delete_task(self, title: str) -> bool:
        """タイトルで最初に一致するタスクをどちらかのセクションから削除し UI を更新する。"""
        if not title:
            return False
        for section in ["現在のタスク", "完了済みのタスク"]:
            tasks_list = self.tasks.get(section, [])
            for idx, task in enumerate(list(tasks_list)):
                if task.get("title") == title:
                    try:
                        del tasks_list[idx]
                    except Exception:
                        return False
                    try:
                        self.refresh_ui()
                    except Exception:
                        pass
                    return True
        return False

    def move_task(self, title: str, destination: str) -> bool:
        """タイトルでタスクを探し destination("現在のタスク" or "完了済みのタスク") へ移動する。"""
        if destination not in ("現在のタスク", "完了済みのタスク"):
            return False
        if not title:
            return False
        # Ensure destination list exists
        if destination not in self.tasks or not isinstance(self.tasks[destination], list):
            self.tasks[destination] = []
        # Search both sections
        for section in ["現在のタスク", "完了済みのタスク"]:
            tasks_list = self.tasks.get(section, [])
            for idx, task in enumerate(list(tasks_list)):
                if task.get("title") == title:
                    # If already in destination just return True (no duplicate move)
                    if section == destination:
                        return True
                    # Move
                    try:
                        moved = tasks_list.pop(idx)
                    except Exception:
                        return False
                    self.tasks[destination].append(moved)
                    try:
                        self.refresh_ui()
                    except Exception:
                        pass
                    return True
        return False

    def _apply_theme(self) -> None:
        mgr = ThemeManager()
        self.setStyleSheet(mgr.get_style_sheet())
        
        # 完了パネルにも新しいスタイルを適用するためにID更新などをトリガー
        self._history_panel.setObjectName("HistoryPanel")
        self._history_panel.style().unpolish(self._history_panel)
        self._history_panel.style().polish(self._history_panel)
        
        # 既存子要素にも適用
        for w in self.findChildren(QLabel):
            w.style().unpolish(w)
            w.style().polish(w)

    def _create_section(self, title, tasks):
        section_widget = SectionWidget(title)
        section_widget.dropped.connect(self.on_task_dropped)

        section_layout = QVBoxLayout()
        if self.is_fullscreen:
            section_layout.setContentsMargins(12, 12, 12, 12)
            section_layout.setSpacing(12)
        else:
            section_layout.setContentsMargins(8, 8, 8, 8)
            section_layout.setSpacing(8)

        # タイトルラベル（左バー付き）
        title_label = QLabel(" " + title) # パディング調整のためスペース追加
        title_label.setObjectName("SectionTitle")
        # フォントサイズのみスケールに合わせて上書き
        title_font = int(28 * self.ui_scale)
        title_label.setStyleSheet(f"font-size: {title_font}px; margin-bottom: 8px;") 
        title_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        section_layout.addWidget(title_label)

        if title == "現在のタスク":
            scroll_area = QWidget() # グリッドを配置するためのコンテナ
            current_grid = QGridLayout()
            current_grid.setSpacing(16)
            current_grid.setContentsMargins(0, 0, 0, 0)
            
            row = 0
            col = 0
            for idx, task in enumerate(tasks):
                task_frame = TaskWidget(task, title)
                # フォーカスタスクの強調（先頭を採用）
                if idx == 0:
                    task_frame.set_focus_enabled(True)
                    self._focus_task_id = task.get("id") or task.get("title")

                task_layout = QVBoxLayout()
                task_layout.setContentsMargins(16, 16, 16, 16)
                
                # タイトル
                task_title_label = QLabel(task["title"])
                task_title_label.setObjectName("TaskTitle")
                task_title_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
                task_title_label.setWordWrap(True)
                task_layout.addWidget(task_title_label)

                # 説明
                if task.get("description"):
                    task_content_label = QLabel(task["description"])
                    task_content_label.setObjectName("TaskDesc")
                    task_content_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
                    task_content_label.setWordWrap(True)
                    task_layout.addWidget(task_content_label)
                
                # スペーサーで上詰め
                task_layout.addStretch()

                task_frame.setLayout(task_layout)
                
                # フォーカスタスクは横幅いっぱい、それ以外はグリッド
                if idx == 0:
                    current_grid.addWidget(task_frame, 0, 0, 1, 2) # colspan 2
                    row = 1
                    col = 0
                else:
                    current_grid.addWidget(task_frame, row, col)
                    col += 1
                    if col >= 2:
                        col = 0
                        row += 1
            section_layout.addLayout(current_grid)
            section_layout.addStretch() # 下余白
        else:
             # 他のセクション（基本的に使われないか、完了済みリストなど）
             pass

        section_widget.setLayout(section_layout)
        return section_widget

    def peek_history_panel(self, offset: int) -> None:
        """ドラッグ中に履歴パネルをチラ見せする"""
        if offset == self._peek_offset:
            return
        self._peek_offset = offset
        
        # パネルが表示中でない場合のみ処理
        # if not self._history_panel.isVisible(): ... としたいが、peekのためにshowする必要あり
        
        if offset > 0:
            if not self._history_panel.isVisible():
                self._position_history_panel(hidden=True)
                self._history_panel.show()
                self._history_panel.raise_()
            
            target_x = self.width() - offset
            self._history_panel.move(target_x, 0)
        else:
            # offset 0 になったら隠す（ただしスワイプで出しているときは別判定が必要かも）
            # 今回はドラッグ終了(drop/leave)で0が来るので隠してOK
            if self._history_panel.isVisible():
                # アニメーションなしですぐ戻すか、隠す
                self._history_panel.move(self.width(), 0)
                self._history_panel.hide()

    def _create_palette(self, color):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, color)
        return palette

    def _clear_layout(self, layout):
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

    def refresh_ui(self):
        main_layout = self.layout()
        if main_layout is None:
            main_layout = QHBoxLayout()
            self.setLayout(main_layout)
        else:
            self._clear_layout(main_layout)

        current_section = self._create_section("現在のタスク", self.tasks.get("現在のタスク", []))
        current_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(current_section)

        self._apply_theme()
        self.update()
        self._update_history_panel()

    def _load_tasks_from_google(self) -> None:
        """Google Tasks からタスクを取得して UI に反映する。"""
        creds = backend.get_credentials()
        service = backend.build_tasks_service(creds)
        tasklists = backend.list_tasklists(service)
        if not tasklists:
            return
        first_list_id = tasklists[0]["id"]
        self.google_tasklist_id = first_list_id
        tasks = backend.list_tasks(service, first_list_id, show_completed=True, show_hidden=True)
        current, done = self._convert_google_tasks_to_sections(tasks)
        self.tasks["現在のタスク"] = current
        self.tasks["完了済みのタスク"] = done
        try:
            self.refresh_ui()
        except Exception:
            pass

    def _convert_google_tasks_to_sections(self, google_tasks: list[dict]) -> tuple[list[dict], list[dict]]:
        current: list[dict] = []
        done_all: list[dict] = []
        for t in google_tasks:
            title = t.get("title") or "(無題)"
            desc = t.get("notes") or ""
            entry = {"title": title, "description": desc, "id": t.get("id"), "completed": t.get("completed")}
            if t.get("status") == "completed":
                done_all.append(entry)
            else:
                current.append(entry)
        # 完了済みは完了日時で降順に並べ、最新2件のみ採用
        def _dt(s: typing.Optional[str]) -> datetime:
            if not s:
                return datetime.min
            try:
                # RFC3339 'Z' を Python 互換に変換
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            except Exception:
                return datetime.min
        done_sorted = sorted(done_all, key=lambda e: _dt(e.get("completed")), reverse=True)
        done_top2 = done_sorted[:2]
        return current, done_top2

    def on_task_dropped(self, payload: dict, destination: str, global_pos: QPoint | None = None) -> None:
        """ドラッグ&ドロップで別セクションへ移動したときにAPI/UI反映。"""
        # 現在のUIから該当タスクを見つける（id 優先）
        task = None
        for sec in ["現在のタスク", "完了済みのタスク"]:
            for t in self.tasks.get(sec, []):
                if payload.get("id") and t.get("id") == payload.get("id"):
                    task = t
                    break
                if not payload.get("id") and t.get("title") == payload.get("title"):
                    task = t
                    break
            if task:
                break
        if not task:
            return
        source = "完了済みのタスク" if self._is_task_in_section(task, "完了済みのタスク") else "現在のタスク"
        if source == destination:
            return

        # 完了などの条件判定
        # すでに dropEvent 側で「画面右側なら完了」と判断して destination="完了済みのタスク" で渡してきているため
        # ここでは座標判定などを厳密に行う必要はない。
        # ただし、完了パネルが全く見えていない状態での誤操作防止等の意図があるなら別だが、
        # 今回は「完了しやすくする」方向で修正するため、条件を緩和する。

        try:
            if not (self.google_tasklist_id and task.get("id")):
                # ローカルのみの場合はAPI呼び出ししないが、一応IDチェック
                # IDがない場合はAPI連携できないので無視するか、ローカル移動のみ行う
                pass 
            
            # API連携部分
            if self.google_tasklist_id and task.get("id"):
                creds = backend.get_credentials()
                service = backend.build_tasks_service(creds)
                if destination == "完了済みのタスク":
                    backend.complete_task(service, self.google_tasklist_id, task["id"])
                else:
                    backend.uncomplete_task(service, self.google_tasklist_id, task["id"])
        except HttpError as e:
            try:
                resp = getattr(e, "resp", None)
                status = getattr(e, "status_code", None) or (resp.status if resp is not None else None)
            except Exception:
                status = None
            if status == 403:
                try:
                    backend.force_reauthorize()
                    creds = backend.get_credentials()
                    service = backend.build_tasks_service(creds)
                    if not self.google_tasklist_id:
                        raise RuntimeError("tasklist_id が不明です")
                    if destination == "完了済みのタスク":
                        backend.complete_task(service, self.google_tasklist_id, task["id"])
                    else:
                        backend.uncomplete_task(service, self.google_tasklist_id, task["id"])
                except Exception as e2:
                    self.raise_error(f"Google Tasksへの反映に失敗しました。認可設定を確認してください。\n{str(e2)}")
                    return
            else:
                self.raise_error(f"Google Tasksへの反映に失敗しました。認可設定を確認してください。\n{str(e)}")
                return
        except Exception as e:
            # APIエラーでもローカル移動は試みるか、エラー表示して止めるか。
            # 今回はエラー表示のみして return (同期ズレを防ぐため)
            # ただし ID がない(ローカルダミー)の場合は例外が出るので無視して進む
            if "tasklist_id" in str(e) or "task id" in str(e):
                pass
            else:
                self.raise_error(str(e))
                return

        try:
            self._move_task_dict(task, destination)
        except Exception:
            pass
        # 完了時のポップアップ表示
        if destination == "完了済みのタスク":
            try:
                self._show_completion_popup(title=task.get("title", ""), duration_ms=self.popup_duration_ms)
                self._show_completion_effects()
                self._nudge_history_panel()
                self._play_complete_sound()
            except Exception:
                pass

    def _move_task_dict(self, task: dict, destination: str) -> None:
        if destination not in ("現在のタスク", "完了済みのタスク"):
            return
        # もとの場所から削除
        for section in ["現在のタスク", "完了済みのタスク"]:
            lst = self.tasks.get(section, [])
            for i, t in enumerate(list(lst)):
                if t is task or (task.get("id") and t.get("id") == task.get("id")):
                    lst.pop(i)
                    break
        # 追加
        if destination not in self.tasks or not isinstance(self.tasks[destination], list):
            self.tasks[destination] = []
        self.tasks[destination].append(task)
        self.refresh_ui()

    def _is_task_in_section(self, task: dict, section: str) -> bool:
        lst = self.tasks.get(section, [])
        for t in lst:
            if t is task:
                return True
            if task.get("id") and t.get("id") == task.get("id"):
                return True
        return False

    def _apply_google_sections(self, current: list, done: list) -> None:
        """スレッドから受け取ったタスクリストをUI状態へ反映。"""
        self.tasks["現在のタスク"] = list(current)
        self.tasks["完了済みのタスク"] = list(done)
        try:
            self.refresh_ui()
        except Exception:
            pass

    def _start_periodic_sync(self, interval_ms: int) -> None:
        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(interval_ms)
        self._sync_timer.timeout.connect(self._sync_google_in_background)
        self._sync_timer.start()

        # 初回も少し遅延して開始
        QTimer.singleShot(2_000, self._sync_google_in_background)

    def _sync_google_in_background(self) -> None:
        try:
            threading.Thread(target=self._fetch_google_tasks_and_emit, daemon=True).start()
        except Exception:
            pass

    def _fetch_google_tasks_and_emit(self) -> None:
        try:
            creds = backend.get_credentials()
            service = backend.build_tasks_service(creds)
            list_id = self.google_tasklist_id
            if not list_id:
                tls = backend.list_tasklists(service)
                if not tls:
                    return
                list_id = tls[0]["id"]
                # 参照だけの更新なので問題なし
                self.google_tasklist_id = list_id
            tasks = backend.list_tasks(service, list_id, show_completed=True, show_hidden=True)
            current, done = self._convert_google_tasks_to_sections(tasks)
            # UIスレッドへ反映依頼
            self.request_set_tasks.emit(current, done)
        except Exception:
            # ネットワークなどの一時的失敗は無視
            pass

    def raise_error(self, message: str) -> None:
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("エラー")
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def _apply_focus_style(self, widget: QWidget) -> None:
        """フォーカスタスクを強調表示。"""
        if isinstance(widget, TaskWidget):
            widget.set_focus_enabled(True)

    def _show_completion_effects(self) -> None:
        """完了時の流れ効果とチェック表示（簡易版）。"""
        flow = QWidget(self)
        flow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        flow.setStyleSheet("QWidget { background-color: rgba(255,255,255,0); }")
        flow.setGeometry(0, 0, self.width(), self.height())
        flow.show()

        bar = QWidget(flow)
        bar.setStyleSheet("QWidget { background-color: rgba(255,255,255,100); }")
        bar.setGeometry(-self.width() // 3, 0, self.width() // 3, self.height())
        bar.show()

        anim = QPropertyAnimation(bar, b"pos", self)
        anim.setDuration(150)
        anim.setStartValue(QPoint(-self.width() // 3, 0))
        anim.setEndValue(QPoint(self.width(), 0))
        bar._anim = anim  # type: ignore[attr-defined]

        check = QLabel("✓", self)
        check.setAlignment(Qt.AlignmentFlag.AlignCenter)
        check.setStyleSheet("QLabel { color: rgba(200,255,200,200); font-size: 48px; }")
        check.adjustSize()
        check.move((self.width() - check.width()) // 2, (self.height() - check.height()) // 2)
        check.show()

        check_effect = QGraphicsOpacityEffect(check)
        check.setGraphicsEffect(check_effect)
        check_anim = QPropertyAnimation(check_effect, b"opacity", self)
        check_anim.setDuration(250)
        check_anim.setStartValue(0.0)
        check_anim.setEndValue(1.0)
        check._anim = check_anim  # type: ignore[attr-defined]

        def _cleanup():
            try:
                check.deleteLater()
                flow.deleteLater()
            except Exception:
                pass

        anim.finished.connect(_cleanup)
        anim.start()
        check_anim.start()

    def _show_completion_popup(self, title: str = "", duration_ms: int | None = None) -> None:
        """完了時に画像＋メッセージを中央に表示してフェードアウト。"""
        # 画像パス解決（スクリプト相対）
        base_dir = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(base_dir, "assets", "rect1.png")

        # オーバーレイ用コンテナ
        popup = QWidget(self)
        popup.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        popup.setStyleSheet("QWidget { background: transparent; }")

        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(8)
        popup.setLayout(vbox)

        # 背景画像（任意）
        img_label = QLabel(popup)
        pix = QPixmap(img_path)
        if not pix.isNull():
            img_label.setPixmap(pix)
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vbox.addWidget(img_label, 0, Qt.AlignmentFlag.AlignHCenter)

        # タスクタイトル
        title_label = QLabel(popup)
        title_label.setText(title or "タスク")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("QLabel { color: #101010; font-size: 24px; font-weight: bold; }")
        vbox.addWidget(title_label, 0, Qt.AlignmentFlag.AlignHCenter)

        # 完了メッセージ
        done_label = QLabel(popup)
        done_label.setText("完了しました！")
        done_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        done_label.setStyleSheet("QLabel { color: #101010; font-size: 20px; }")
        vbox.addWidget(done_label, 0, Qt.AlignmentFlag.AlignHCenter)

        # ねぎらいの言葉
        thanks_label = QLabel(popup)
        thanks_label.setText("お疲れさま！よく頑張りました。")
        thanks_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thanks_label.setStyleSheet("QLabel { color: #2a6; font-size: 18px; }")
        vbox.addWidget(thanks_label, 0, Qt.AlignmentFlag.AlignHCenter)

        popup.adjustSize()

        # 画面中央へ配置
        w = self.width()
        h = self.height()
        pw = popup.width()
        ph = popup.height()
        popup.move(max(0, (w - pw) // 2), max(0, (h - ph) // 2))
        popup.show()

        # フェードアウトアニメーション
        effect = QGraphicsOpacityEffect(popup)
        popup.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(duration_ms if duration_ms is not None else 2000)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        popup._anim = anim  # type: ignore[attr-defined]

        def _cleanup():
            try:
                popup.hide()
                popup.deleteLater()
            except Exception:
                pass

        anim.finished.connect(_cleanup)
        anim.start()

    def _setup_complete_sound(self, sound_path: str) -> None:
        if not os.path.exists(sound_path):
            return
        ext = os.path.splitext(sound_path)[1].lower()
        if ext in (".wav", ".ogg"):
            snd = QSoundEffect(self)
            snd.setSource(QUrl.fromLocalFile(sound_path))
            snd.setVolume(0.6)
            self._complete_sound = snd
            return
        # mp3 は QMediaPlayer を使う
        audio = QAudioOutput(self)
        audio.setVolume(0.6)
        player = QMediaPlayer(self)
        player.setAudioOutput(audio)
        player.setSource(QUrl.fromLocalFile(sound_path))
        self._complete_audio = audio
        self._complete_player = player

    def _play_complete_sound(self) -> None:
        if self._complete_sound is not None:
            if self._complete_sound.isLoaded():
                self._complete_sound.play()
            return
        if self._complete_player is not None:
            self._complete_player.stop()
            self._complete_player.play()

    def _build_menu_contents(self) -> None:
        """上端メニューの仮コンテンツを構築。"""
        title = QLabel("メニュー", self._menu_panel)
        title.setStyleSheet("QLabel { color: white; font-size: 20px; font-weight: bold; }")
        self._menu_panel_layout.addWidget(title)
        
        # テーマ切り替え
        theme_btn = QPushButton("ダークモード切替", self._menu_panel)
        theme_btn.setStyleSheet(
            "QPushButton { background-color: rgba(255,255,255,0.12); color: white; padding: 8px; }"
        )
        theme_btn.clicked.connect(self._action_toggle_theme)
        self._menu_panel_layout.addWidget(theme_btn)

        exit_btn = QPushButton("終了", self._menu_panel)
        exit_btn.setStyleSheet(
            "QPushButton { background-color: rgba(255,255,255,0.12); color: white; padding: 8px; }"
        )
        exit_btn.clicked.connect(self._action_exit)
        self._menu_panel_layout.addWidget(exit_btn)

        ver_btn = QPushButton("バージョン情報", self._menu_panel)
        ver_btn.setStyleSheet(
            "QPushButton { background-color: rgba(255,255,255,0.12); color: white; padding: 8px; }"
        )
        ver_btn.clicked.connect(self._action_version)
        self._menu_panel_layout.addWidget(ver_btn)
        
    def _action_toggle_theme(self) -> None:
        ThemeManager().toggle_theme()
        # メニュー閉じてから適用
        self._hide_menu_panel()
        self.refresh_ui()

    def _update_history_panel(self) -> None:
        """右端の履歴パネル内容を更新。"""
        # 既存削除
        while self._history_panel_layout.count():
            item = self._history_panel_layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()
        
        # ThemeManagerのQSSに任せるため個別設定は削除
        title = QLabel("完了済み", self._history_panel)
        # フォントサイズなどの構造的スタイルは残して良いが、色はQSSに任せる
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 8px;")
        self._history_panel_layout.addWidget(title)

        for t in self.tasks.get("完了済みのタスク", [])[:5]:
            card = QFrame(self._history_panel)
            card.setObjectName("CompletedCard") # QSSで装飾
            
            card_layout = QVBoxLayout()
            card_layout.setContentsMargins(12, 10, 12, 10)
            card_layout.setSpacing(4)
            card.setLayout(card_layout)

            lbl = QLabel(t.get("title", "(無題)"), card)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("font-size: 14px; background: transparent; border: none;")
            card_layout.addWidget(lbl)
            self._history_panel_layout.addWidget(card)

        self._history_panel.adjustSize()
        self._position_history_panel(hidden=True)

    def _position_history_panel(self, hidden: bool) -> None:
        width = min(280, max(220, self.width() // 4))
        height = self.height()
        self._history_panel.resize(width, height)
        x = self.width() if hidden else self.width() - width
        self._history_panel.move(x, 0)

    def _show_history_panel(self) -> None:
        self._position_history_panel(hidden=True)
        self._history_panel.show()
        self._history_panel.raise_()
        anim = QPropertyAnimation(self._history_panel, b"pos", self)
        anim.setDuration(200)
        anim.setStartValue(QPoint(self.width(), 0))
        anim.setEndValue(QPoint(self.width() - self._history_panel.width(), 0))
        self._history_panel._anim = anim  # type: ignore[attr-defined]
        anim.start()
        self._history_panel_timer.start(3000)

    def _hide_history_panel(self) -> None:
        if not self._history_panel.isVisible():
            return
        anim = QPropertyAnimation(self._history_panel, b"pos", self)
        anim.setDuration(160)
        anim.setStartValue(self._history_panel.pos())
        anim.setEndValue(QPoint(self.width(), 0))
        self._history_panel._anim = anim  # type: ignore[attr-defined]
        def _finish():
            self._history_panel.hide()
        anim.finished.connect(_finish)
        anim.start()

    def _nudge_history_panel(self) -> None:
        """完了後の“ぴょこっ”演出。"""
        if not self._history_panel.isVisible():
            self._history_panel.show()
        self._history_panel.raise_()
        base_x = self.width() - self._history_panel.width()
        self._history_panel.move(self.width(), 0)
        anim = QPropertyAnimation(self._history_panel, b"pos", self)
        anim.setDuration(120)
        anim.setStartValue(QPoint(self.width(), 0))
        anim.setEndValue(QPoint(base_x - 20, 0))
        self._history_panel._anim = anim  # type: ignore[attr-defined]
        def _back():
            anim2 = QPropertyAnimation(self._history_panel, b"pos", self)
            anim2.setDuration(120)
            anim2.setStartValue(QPoint(base_x - 20, 0))
            anim2.setEndValue(QPoint(self.width(), 0))
            self._history_panel._anim2 = anim2  # type: ignore[attr-defined]
            anim2.finished.connect(self._history_panel.hide)
            anim2.start()
        anim.finished.connect(_back)
        anim.start()

    def _show_menu_panel(self) -> None:
        h = min(260, max(200, self.height() // 3))
        self._menu_panel.resize(self.width(), h)
        self._menu_panel.move(0, -h)
        self._menu_panel.show()
        self._menu_panel.raise_()
        anim = QPropertyAnimation(self._menu_panel, b"pos", self)
        anim.setDuration(150)
        anim.setStartValue(QPoint(0, -h))
        anim.setEndValue(QPoint(0, 0))
        self._menu_panel._anim = anim  # type: ignore[attr-defined]
        anim.start()

    def _hide_menu_panel(self) -> None:
        if not self._menu_panel.isVisible():
            return
        h = self._menu_panel.height()
        anim = QPropertyAnimation(self._menu_panel, b"pos", self)
        anim.setDuration(120)
        anim.setStartValue(self._menu_panel.pos())
        anim.setEndValue(QPoint(0, -h))
        self._menu_panel._anim = anim  # type: ignore[attr-defined]
        def _finish():
            self._menu_panel.hide()
        anim.finished.connect(_finish)
        anim.start()

    def _action_exit(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _action_version(self) -> None:
        QMessageBox.information(self, "バージョン情報", "Shibarania v0.9")

    def _edge_hold_timeout(self) -> None:
        # キャンセル時の保持後にクローズ
        if self._edge_mode == "right":
            self._hide_history_panel()
        if self._edge_mode == "top":
            self._hide_menu_panel()

    def eventFilter(self, a0, a1):
        if a1 is None:
            return super().eventFilter(a0, a1)
        if a1.type() == QEvent.Type.MouseButtonPress and isinstance(a1, QMouseEvent):
            # メニュー表示中に外側クリックで閉じる
            if self._menu_panel.isVisible() and a1.pos().y() > self._menu_panel.height():
                self._hide_menu_panel()
                return True
        if a1.type() == QEvent.Type.MouseButtonPress and isinstance(a1, QMouseEvent):
            pos = a1.pos()
            if pos.x() >= self.width() - 60:
                self._edge_mode = "right"
                self._edge_press_pos = pos
                self._edge_swipe_distance = 0
                return False
            if pos.y() <= 40:
                self._edge_mode = "top"
                self._edge_press_pos = pos
                self._edge_swipe_distance = 0
                return False
        if a1.type() == QEvent.Type.MouseMove and self._edge_press_pos is not None and isinstance(a1, QMouseEvent):
            pos = a1.pos()
            if self._edge_mode == "right":
                self._edge_swipe_distance = max(0, self._edge_press_pos.x() - pos.x())
                return False
            if self._edge_mode == "top":
                self._edge_swipe_distance = max(0, pos.y() - self._edge_press_pos.y())
                return False
        if a1.type() == QEvent.Type.MouseButtonRelease and self._edge_press_pos is not None:
            if self._edge_mode == "right":
                if self._edge_swipe_distance >= 40:
                    self._show_history_panel()
                else:
                    self._edge_hold_timer.start(500)
            elif self._edge_mode == "top":
                if self._edge_swipe_distance >= 30:
                    self._show_menu_panel()
                else:
                    # タップでは開かない
                    self._edge_hold_timer.start(500)
            self._edge_press_pos = None
            self._edge_swipe_distance = 0
            return False
        return super().eventFilter(a0, a1)


class Task(typing.TypedDict):
    title: str
    description: str


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    fullscreen = "--fullscreen" in sys.argv or "-f" in sys.argv
    window = Shibarania(fullscreen=fullscreen)
    if fullscreen:
        window.showFullScreen()
    else:
        window.show()
    sys.exit(app.exec())
