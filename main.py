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
try:
    from googleapiclient.errors import HttpError
except Exception:
    HttpError = Exception


class TaskWidget(QFrame):
    def __init__(self, task_data: dict, section: str):
        super().__init__()
        self.task_data = task_data
        self.section = section
        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(1)
        self._press_timer = QTimer(self)
        self._press_timer.setSingleShot(True)
        self._press_timer.timeout.connect(self._on_long_press)
        self._hint_timer = QTimer(self)
        self._hint_timer.setSingleShot(True)
        self._hint_timer.timeout.connect(self._show_hint_arrow)
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
            # 長押し前に大きく動いたらキャンセル
            if (a0.pos() - self._press_pos).manhattanLength() > 6:
                self._cancel_press()
            return
        # 長押し成立後はドラッグ開始
        self._start_drag()

    def mouseReleaseEvent(self, a0):
        self._cancel_press()
        super().mouseReleaseEvent(a0)

    def _apply_press_feedback(self) -> None:
        # 影を少し濃く、背景色をわずかに暗く
        self._press_active = True
        self._update_style()

    def _on_long_press(self) -> None:
        self._long_pressed = True
        # 浮かせる
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)
        # ヒント矢印は150ms後
        self._hint_timer.start(150)
        # 長押し成立時に完了パネルを表示
        try:
            win = self.window()
            if hasattr(win, "_show_history_panel"):
                win._show_history_panel()
        except Exception:
            pass

    def _show_hint_arrow(self) -> None:
        if self._hint_label is not None:
            return
        self._hint_label = QLabel(self)
        # 画像ヒント（半透明）
        base_dir = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(base_dir, "assets", "yajirushi.png")
        pix = QPixmap(img_path)
        if not pix.isNull():
            self._hint_label.setPixmap(pix)
            self._hint_label.adjustSize()
        else:
            self._hint_label.setText("→")
            self._hint_label.setStyleSheet("QLabel { color: rgba(255,255,255,180); font-size: 20px; }")
            self._hint_label.adjustSize()
        self._hint_label.move(self.width() - self._hint_label.width() - 8, 8)
        self._hint_effect = QGraphicsOpacityEffect(self._hint_label)
        self._hint_label.setGraphicsEffect(self._hint_effect)
        anim = QPropertyAnimation(self._hint_effect, b"opacity", self)
        anim.setDuration(150)
        anim.setStartValue(0.0)
        anim.setEndValue(0.35)
        self._hint_label._anim = anim  # type: ignore[attr-defined]
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
        drag.exec()
        self._cancel_press()

    def _cancel_press(self) -> None:
        self._press_timer.stop()
        self._press_feedback_timer.stop()
        self._hint_timer.stop()
        self._press_pos = None
        self._long_pressed = False
        self._press_active = False
        # フォーカス影を維持
        if self._is_focus:
            try:
                shadow = QGraphicsDropShadowEffect(self)
                shadow.setBlurRadius(22)
                shadow.setOffset(0, 4)
                shadow.setColor(QColor(0, 0, 0, 90))
                self._focus_shadow = shadow
                self.setGraphicsEffect(shadow)
            except Exception:
                self._focus_shadow = None
                self.setGraphicsEffect(None)
        else:
            self.setGraphicsEffect(None)
        self._update_style()
        if self._hint_label:
            self._hint_label.hide()
            self._hint_label.deleteLater()
            self._hint_label = None
            self._hint_effect = None

    def set_focus_enabled(self, enabled: bool) -> None:
        self._is_focus = enabled
        if enabled:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(22)
            shadow.setOffset(0, 4)
            shadow.setColor(QColor(0, 0, 0, 90))
            self._focus_shadow = shadow
            self.setGraphicsEffect(shadow)
        else:
            self._focus_shadow = None
        self._update_style()

    def _update_style(self) -> None:
        styles = []
        if self._is_focus:
            styles.append("QFrame { border: 2px solid rgba(120, 200, 255, 120); }")
        if self._press_active:
            styles.append("QFrame { background-color: rgba(0,0,0,0.03); }")
        self.setStyleSheet(" ".join(styles))


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
        else:
            a0.ignore()
    
    def dropEvent(self, a0):
        if not a0:
            return
        mime = a0.mimeData()
        if not mime:
            a0.ignore()
            return
        try:
            data = mime.data("application/x-shibarania-task")
            payload = json.loads(bytes(data.data()).decode("utf-8"))
            self.dropped.emit(payload, self.section_name, self.mapToGlobal(a0.position().toPoint()))
            a0.acceptProposedAction()
        except Exception:
            a0.ignore()


class Shibarania(QWidget):
    # Console thread-safe requests into the UI thread
    request_add_task = pyqtSignal(str, str)
    request_delete_task = pyqtSignal(str)
    request_move_task = pyqtSignal(str, str)  # title, destination section
    request_set_tasks = pyqtSignal(list, list)  # current, done

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
        current_section = self._create_section(
            "現在のタスク", QColor(200, 255, 200), self.tasks["現在のタスク"]
        )
        current_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(current_section, 2)

        self.setLayout(layout)

        # 完了済み履歴パネル（右端スワイプ）
        self._history_panel = SectionWidget("完了済みのタスク")
        self._history_panel.setParent(self)
        self._history_panel.setAutoFillBackground(True)
        self._history_panel.setStyleSheet("QWidget { background-color: rgba(200, 200, 255, 180); }")
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

    def _create_section(self, title, color, tasks):
        section_widget = SectionWidget(title)
        section_widget.setAutoFillBackground(True)
        section_widget.setPalette(self._create_palette(color))
        section_widget.dropped.connect(self.on_task_dropped)

        section_layout = QVBoxLayout()
        if self.is_fullscreen:
            section_layout.setContentsMargins(6, 6, 6, 6)
            section_layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setAutoFillBackground(True)
        title_label.setPalette(self._create_palette(color))
        title_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        title_font = int(28 * self.ui_scale)
        title_label.setStyleSheet(f"QLabel {{ color : #101010; font-size : {title_font}px; padding: 0px; }}")
        title_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        section_layout.addWidget(title_label, 0, Qt.AlignmentFlag.AlignHCenter)

        if title == "現在のタスク":
            current_grid = QGridLayout()
            section_layout.addLayout(current_grid)
            row = 0
            col = 0
            for idx, task in enumerate(tasks):
                task_frame = TaskWidget(task, title)
                # フォーカスタスクの強調（先頭を採用）
                if idx == 0:
                    self._apply_focus_style(task_frame)
                    self._focus_task_id = task.get("id") or task.get("title")

                task_layout = QVBoxLayout()
                task_title_label = QLabel(task["title"])
                task_title_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
                task_title_font = int(24 * self.ui_scale)
                task_title_label.setStyleSheet(
                    f"QLabel {{ font-weight: bold; color : #101010; font-size : {task_title_font}px;}}"
                )
                task_title_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                task_layout.addWidget(task_title_label)

                if task.get("description"):
                    task_content_label = QLabel(task["description"])
                    task_content_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                    task_content_font = int(18 * self.ui_scale)
                    task_content_label.setStyleSheet(
                        f"QLabel {{ color : #101010; font-size : {task_content_font}px; }}"
                    )
                    task_layout.addWidget(task_content_label)

                task_frame.setLayout(task_layout)
                current_grid.addWidget(task_frame, row, col)
                col += 1
                if col >= 2:
                    col = 0
                    row += 1
        else:
            for task in tasks:
                task_frame = TaskWidget(task, title)

                task_layout = QVBoxLayout()
                task_title_label = QLabel(task["title"])
                task_title_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
                task_title_font = int(24 * self.ui_scale)
                task_title_label.setStyleSheet(
                    f"QLabel {{ font-weight: bold; color : #101010; font-size : {task_title_font}px;}}"
                )
                task_title_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                task_layout.addWidget(task_title_label)

                if task.get("description"):
                    task_content_label = QLabel(task["description"])
                    task_content_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                    task_content_font = int(18 * self.ui_scale)
                    task_content_label.setStyleSheet(
                        f"QLabel {{ color : #101010; font-size : {task_content_font}px; }}"
                    )
                    task_layout.addWidget(task_content_label)

                task_frame.setLayout(task_layout)
                section_layout.addWidget(task_frame)

        section_widget.setLayout(section_layout)
        return section_widget

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

        current_section = self._create_section(
            "現在のタスク", QColor(200, 255, 200), self.tasks.get("現在のタスク", [])
        )
        current_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(current_section)

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

        # 完了判定は「完了パネルが表示中」かつ「ドロップ位置が完了パネル内」
        if destination == "完了済みのタスク":
            if not self._history_panel.isVisible():
                return
            if global_pos is not None and not self._history_panel.geometry().contains(self.mapFromGlobal(global_pos)):
                return

        try:
            if not (self.google_tasklist_id and task.get("id")):
                raise RuntimeError("tasklist_id または task id がありません")
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
        title = QLabel("完了済み", self._history_panel)
        title.setStyleSheet("QLabel { color: #101010; font-size: 16px; font-weight: bold; }")
        self._history_panel_layout.addWidget(title)

        for t in self.tasks.get("完了済みのタスク", [])[:5]:
            card = QFrame(self._history_panel)
            card.setStyleSheet(
                "QFrame { background-color: rgba(200, 200, 255, 140); border: 1px solid #101010; border-radius: 6px; }"
            )
            card_layout = QVBoxLayout()
            card_layout.setContentsMargins(8, 6, 8, 6)
            card_layout.setSpacing(4)
            card.setLayout(card_layout)

            lbl = QLabel(t.get("title", "(無題)"), card)
            lbl.setStyleSheet("QLabel { color: #101010; font-size: 14px; }")
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
