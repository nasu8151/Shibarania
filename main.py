import sys
import typing
import threading
import json
import os
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QLabel, QHBoxLayout, QVBoxLayout, QWidget, QFrame, QSizePolicy, QGridLayout, QMessageBox, QGraphicsOpacityEffect
from PyQt6.QtGui import QPalette, QColor, QDrag, QPixmap
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QMimeData, QPropertyAnimation
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

    def mousePressEvent(self, a0):
        if not a0:
            return
        if a0.button() == Qt.MouseButton.LeftButton:
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
        else:
            super().mousePressEvent(a0)


class SectionWidget(QWidget):
    dropped = pyqtSignal(object, str)  # payload, destination name

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
            payload = json.loads(bytes(data).decode("utf-8"))
            self.dropped.emit(payload, self.section_name)
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

        # ポップアップ表示時間（ミリ秒）
        self.popup_duration_ms: int = 4000

        # Google Tasklist ID（先頭のリストを利用）
        self.google_tasklist_id: typing.Optional[str] = None

        self.tasks = {
            "現在のタスク": [
                {"title": "TaskB", "description": "Example"},
                {"title": "TaskD", "description": " "},
                {"title": "TaskE", "description": " "},
                {"title": "TaskF", "description": " "},
                {"title": "TaskG", "description": " "},
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

        done_section = self._create_section(
            "完了済みのタスク", QColor(200, 200, 255), self.tasks["完了済みのタスク"]
        )
        done_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(done_section, 1)

        self.setLayout(layout)

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

        done_section = self._create_section(
            "完了済みのタスク", QColor(200, 200, 255), self.tasks.get("完了済みのタスク", [])
        )
        done_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(done_section)

        self.update()

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

    def on_task_dropped(self, payload: dict, destination: str) -> None:
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
