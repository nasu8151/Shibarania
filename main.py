import sys
import typing
from PyQt6.QtWidgets import QApplication, QLabel, QHBoxLayout, QVBoxLayout, QWidget, QFrame, QSizePolicy, QGridLayout, QMessageBox
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt, pyqtSignal
import backend
try:
    from googleapiclient.errors import HttpError
except Exception:
    HttpError = Exception


class TaskWidget(QFrame):
    clicked = pyqtSignal(object)  # emits task dict

    def __init__(self, task_data: dict):
        super().__init__()
        self.task_data = task_data
        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(1)

    def mouseReleaseEvent(self, a0):
        try:
            self.clicked.emit(self.task_data)
        finally:
            super().mouseReleaseEvent(a0)


class Shibarania(QWidget):
    # Console thread-safe requests into the UI thread
    request_add_task = pyqtSignal(str, str)
    request_delete_task = pyqtSignal(str)
    request_move_task = pyqtSignal(str, str)  # title, destination section

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shibarania")
        self.setGeometry(100, 100, 800, 480)

        # Google Tasklist ID（先頭のリストを利用）
        self.google_tasklist_id: typing.Optional[str] = None

        self.tasks = {
            "現在のタスク": [
                {"title": "TaskB", "description": " "},
                {"title": "TaskD", "description": " "},
                {"title": "TaskE", "description": " "},
                {"title": "TaskF", "description": " "},
                {"title": "TaskG", "description": "Omochikun!?!?"},
            ],
            "完了済みのタスク": [
                {"title": "TaskO", "description": " "},
            ],
        }

        # レイアウト作成
        layout = QHBoxLayout()

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

        # Google Tasks から初期タスクを読み込み
        try:
            self._load_tasks_from_google()
        except Exception:
            # 認可未設定やネットワーク障害時などは初期データのまま表示
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
        section_layout = QVBoxLayout()

        title_label = QLabel(title)
        title_label.setAutoFillBackground(True)
        title_label.setPalette(self._create_palette(color))
        title_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        title_label.setStyleSheet("QLabel { color : #101010; font-size : 28px; padding: 0px; }")
        title_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        section_layout.addWidget(title_label, 0, Qt.AlignmentFlag.AlignHCenter)

        if title == "現在のタスク":
            current_grid = QGridLayout()
            section_layout.addLayout(current_grid)
            row = 0
            col = 0
            for task in tasks:
                task_frame = TaskWidget(task)

                task_layout = QVBoxLayout()
                task_title_label = QLabel(task["title"])
                task_title_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
                task_title_label.setStyleSheet("QLabel { font-weight: bold; color : #101010; font-size : 18px;}")
                task_title_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                task_layout.addWidget(task_title_label)

                if task.get("description"):
                    task_content_label = QLabel(task["description"])
                    task_content_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                    task_content_label.setStyleSheet("QLabel { color : #101010; }")
                    task_layout.addWidget(task_content_label)

                task_frame.setLayout(task_layout)
                task_frame.clicked.connect(self.on_task_clicked)
                current_grid.addWidget(task_frame, row, col)
                col += 1
                if col >= 2:
                    col = 0
                    row += 1
        else:
            for task in tasks:
                task_frame = TaskWidget(task)

                task_layout = QVBoxLayout()
                task_title_label = QLabel(task["title"])
                task_title_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
                task_title_label.setStyleSheet("QLabel { font-weight: bold; color : #101010; font-size : 18px;}")
                task_title_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                task_layout.addWidget(task_title_label)

                if task.get("description"):
                    task_content_label = QLabel(task["description"])
                    task_content_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                    task_content_label.setStyleSheet("QLabel { color : #101010; }")
                    task_layout.addWidget(task_content_label)

                task_frame.setLayout(task_layout)
                task_frame.clicked.connect(self.on_task_clicked)
                section_layout.addWidget(task_frame)

        section_widget = QWidget()
        section_widget.setLayout(section_layout)
        section_widget.setAutoFillBackground(True)
        section_widget.setPalette(self._create_palette(color))
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
        tasks = backend.list_tasks(service, first_list_id, show_completed=True, show_hidden=False)
        current, done = self._convert_google_tasks_to_sections(tasks)
        self.tasks["現在のタスク"] = current
        self.tasks["完了済みのタスク"] = done
        try:
            self.refresh_ui()
        except Exception:
            pass

    def _convert_google_tasks_to_sections(self, google_tasks: list[dict]) -> tuple[list[dict], list[dict]]:
        current: list[dict] = []
        done: list[dict] = []
        for t in google_tasks:
            title = t.get("title") or "(無題)"
            desc = t.get("notes") or ""
            entry = {"title": title, "description": desc, "id": t.get("id")}
            if t.get("status") == "completed":
                done.append(entry)
            else:
                current.append(entry)
        return current, done

    def on_task_clicked(self, task: dict) -> None:
        """タスククリック時に完了確認を行い、OKならUIとAPIへ反映。"""
        # 完了済みセクションのタスクなら情報だけ表示して終了
        if self._is_task_in_section(task, "完了済みのタスク"):
            info = QMessageBox(self)
            info.setIcon(QMessageBox.Icon.Information)
            info.setWindowTitle("情報")
            info.setText("このタスクはすでに完了済みです。")
            info.setStandardButtons(QMessageBox.StandardButton.Ok)
            info.exec()
            return

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("確認")
        msg.setText("このタスクを完了しますか？")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        result = msg.exec()
        if result == QMessageBox.StandardButton.Ok:
            # APIへ反映
            try:
                if self.google_tasklist_id and task.get("id"):
                    creds = backend.get_credentials()
                    service = backend.build_tasks_service(creds)
                    backend.complete_task(service, self.google_tasklist_id, task["id"])
                else:
                    raise RuntimeError("tasklist_id または task id がありません")
            except HttpError as e:
                # スコープ不足 403 の場合は強制再認可して 1 回だけリトライ
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
                        list_id = self.google_tasklist_id
                        if not list_id:
                            raise RuntimeError("tasklist_id が不明です")
                        backend.complete_task(service, list_id, task["id"])
                    except Exception as e2:
                        warn = QMessageBox(self)
                        warn.setIcon(QMessageBox.Icon.Warning)
                        warn.setWindowTitle("エラー")
                        warn.setText("Google Tasksへの反映に失敗しました。認可設定を確認してください。")
                        warn.setDetailedText(str(e2))
                        warn.setStandardButtons(QMessageBox.StandardButton.Ok)
                        warn.exec()
                        return
                else:
                    warn = QMessageBox(self)
                    warn.setIcon(QMessageBox.Icon.Warning)
                    warn.setWindowTitle("エラー")
                    warn.setText("Google Tasksへの反映に失敗しました。認可設定を確認してください。")
                    warn.setDetailedText(str(e))
                    warn.setStandardButtons(QMessageBox.StandardButton.Ok)
                    warn.exec()
                    return
            except Exception as e:
                warn = QMessageBox(self)
                warn.setIcon(QMessageBox.Icon.Warning)
                warn.setWindowTitle("エラー")
                warn.setText("Google Tasksへの反映に失敗しました。認可設定を確認してください。")
                warn.setDetailedText(str(e))
                warn.setStandardButtons(QMessageBox.StandardButton.Ok)
                warn.exec()
                return
            # UI移動
            try:
                self._move_task_dict(task, "完了済みのタスク")
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


class Task(typing.TypedDict):
    title: str
    description: str


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    window = Shibarania()
    window.show()
    sys.exit(app.exec())
